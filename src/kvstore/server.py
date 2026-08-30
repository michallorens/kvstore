import pickle
import socket
import struct
from typing import Any

from kvstore.engine import KVStoreEngine


class KVServer:
    def __init__(
        self,
        store: KVStoreEngine,
        host: str = "127.0.0.1",
        port: int = 9000,
    ) -> None:
        self.store = store
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

    def _handle(self, request: dict[str, Any]) -> Any:
        operation = request["operation"]

        if operation == "put":
            self.store.put(
                request["key"],
                request["value"],
            )
            return None

        if operation == "read":
            return self.store.read(request["key"])

        if operation == "range":
            return self.store.read_key_range(
                request["start"],
                request["end"],
            )

        if operation == "batch_put":
            self.store.batch_put(
                request["keys"],
                request["values"],
            )
            return None

        if operation == "delete":
            self.store.delete(request["key"])
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
    def _recv_message(cls, conn: socket.socket) -> Any:
        header = cls._recv_exact(conn, 4)

        if header is None:
            return None

        size = struct.unpack(">I", header)[0]
        payload = cls._recv_exact(conn, size)

        if payload is None:
            raise ConnectionError("connection closed")

        return pickle.loads(payload)

    @staticmethod
    def _send_message(
        conn: socket.socket,
        message: Any,
    ) -> None:
        payload = pickle.dumps(message)
        header = struct.pack(">I", len(payload))

        conn.sendall(header + payload)
