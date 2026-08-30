import socket
import struct

from kvstore.server import pack_bytes, pack_pair, unpack_batch

PUT = 0
READ = 1
RANGE = 2
BATCH_PUT = 3
DELETE = 4


class KVClient:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9000,
    ) -> None:
        self.sock = socket.create_connection((host, port))

    def _send(self, operation: int, payload: bytes = b"") -> bytes:
        message = operation.to_bytes(1) + payload
        self.sock.sendall(struct.pack(">I", len(message)) + message)

        header = self._recv_exact(4)
        size = struct.unpack(">I", header)[0]

        return self._recv_exact(size)

    def put(self, key: bytes, value: bytes) -> None:
        self._send(PUT, pack_pair(key, value))

    def read(self, key: bytes) -> bytes | None:
        response = self._send(READ, pack_bytes(key))
        return response or None

    def delete(self, key: bytes) -> None:
        self._send(DELETE, pack_bytes(key))

    def range(self, start: bytes, end: bytes):
        response = self._send(RANGE, pack_pair(start, end))
        return unpack_batch(response)

    def batch_put(
        self,
        keys: list[bytes],
        values: list[bytes],
    ) -> None:
        payload = b""

        for key, value in zip(keys, values):
            payload += pack_pair(key, value)

        self._send(BATCH_PUT, payload)

    def _recv_exact(self, size: int) -> bytes:
        data = bytearray()

        while len(data) < size:
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                raise ConnectionError("connection closed")
            data.extend(chunk)

        return bytes(data)
