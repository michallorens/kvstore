import pickle
import socket
import struct


class KVClient:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9000,
    ) -> None:
        self.sock = socket.create_connection((host, port))

    def _send(self, request):
        payload = pickle.dumps(request)
        self.sock.sendall(struct.pack(">I", len(payload)) + payload)

        header = self._recv_exact(4)
        size = struct.unpack(">I", header)[0]

        return pickle.loads(self._recv_exact(size))

    def _recv_exact(self, size: int) -> bytes:
        data = bytearray()

        while len(data) < size:
            chunk = self.sock.recv(size - len(data))

            if not chunk:
                raise ConnectionError("connection closed")

            data.extend(chunk)

        return bytes(data)

    def put(self, key: bytes, value: bytes) -> None:
        self._send(
            {
                "operation": "put",
                "key": key,
                "value": value,
            }
        )

    def read(self, key: bytes):
        return self._send(
            {
                "operation": "read",
                "key": key,
            }
        )

    def delete(self, key: bytes) -> None:
        self._send(
            {
                "operation": "delete",
                "key": key,
            }
        )

    def range(self, start: bytes, end: bytes):
        return self._send(
            {
                "operation": "range",
                "start": start,
                "end": end,
            }
        )

    def batch_put(
        self,
        keys: list[bytes],
        values: list[bytes],
    ) -> None:
        self._send(
            {
                "operation": "batch_put",
                "keys": keys,
                "values": values,
            }
        )
