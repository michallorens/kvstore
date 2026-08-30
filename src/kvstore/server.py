import socket
import struct
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from kvstore.main import KVStoreAPI

PUT = 0
READ = 1
RANGE = 2
BATCH_PUT = 3
DELETE = 4


def pack_bytes(value: bytes) -> bytes:
    return len(value).to_bytes(4, "big") + value


def pack_pair(key: bytes, value: bytes) -> bytes:
    return pack_bytes(key) + pack_bytes(value)


def unpack_bytes(payload: bytes) -> bytes:
    size = int.from_bytes(payload[:4], "big")
    return payload[4 : 4 + size]


def unpack_pair(payload: bytes) -> tuple[bytes, bytes]:
    key_size = int.from_bytes(payload[:4], "big")
    offset = key_size + 4
    key = payload[4:offset]
    value_size = int.from_bytes(payload[offset : offset + 4], "big")
    offset += 4
    value = payload[offset : offset + value_size]

    return key, value


def unpack_batch(payload: bytes) -> tuple[list[bytes], list[bytes]]:
    keys = []
    values = []

    while len(payload) > 0:
        key, value = unpack_pair(payload)
        keys.append(key)
        values.append(value)
        payload = payload[len(key) + len(value) + 8 :]

    return keys, values


class KVServer:
    def __init__(
        self,
        api: "KVStoreAPI",
        host: str = "127.0.0.1",
        port: int = 9000,
    ) -> None:
        self.api = api
        self.host = host
        self.port = port

    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen()

            print(f"KV server listening on {self.host}:{self.port}")

            while True:
                conn, address = server.accept()

                try:
                    self._serve_connection(conn)
                except ConnectionError:
                    pass
                finally:
                    conn.close()

    def _serve_connection(self, conn: socket.socket) -> None:
        while True:
            request = self._recv_message(conn)

            if request is None:
                return

            response = self._handle(request)
            self._send_message(conn, response)

    @classmethod
    def _pack_range(cls, range: dict[bytes, bytes]) -> bytes:
        payload = b""

        for key, value in range.items():
            payload += pack_pair(key, value)

        return payload

    def _handle(self, request: bytes) -> Any:
        operation = request[0]
        payload = request[1:]

        if operation == PUT:
            key, value = unpack_pair(payload)
            self.api.put(key, value)
            return None

        if operation == READ:
            key = unpack_bytes(payload)
            return self.api.read(key)

        if operation == RANGE:
            start, end = unpack_pair(payload)
            return self._pack_range(self.api.read_key_range(start, end))

        if operation == BATCH_PUT:
            keys, values = unpack_batch(payload)
            self.api.batch_put(keys, values)
            return None

        if operation == DELETE:
            key = unpack_bytes(payload)
            self.api.delete(key)
            return None

        raise ValueError(f"unknown operation: {operation}")

    @staticmethod
    def _recv_exact(
        conn: socket.socket,
        size: int,
    ) -> bytes | None:
        data = bytearray()

        while len(data) < size:
            chunk = conn.recv(size - len(data))

            if not chunk:
                if not data:
                    return None
                raise ConnectionError("connection closed mid-message")

            data.extend(chunk)

        return bytes(data)

    @classmethod
    def _recv_message(cls, conn: socket.socket) -> bytes | None:
        header = cls._recv_exact(conn, 4)

        if header is None:
            return None

        size = struct.unpack(">I", header)[0]
        return cls._recv_exact(conn, size)

    @staticmethod
    def _send_message(
        conn: socket.socket,
        message: bytes | None,
    ) -> None:
        payload = message or b""
        header = struct.pack(">I", len(payload))
        conn.sendall(header + payload)
