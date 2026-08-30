from typing import Iterator

from kvstore.config import Config
from kvstore.engine import KVStoreEngine
from kvstore.record import Record
from kvstore.server import KVServer


class KVStoreAPI:
    def __init__(self, config: Config = Config()) -> None:
        self._engine = KVStoreEngine(config)

    def __enter__(self) -> "KVStoreAPI":
        self._engine.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._engine.close()

    def put(self, key: bytes, value: bytes) -> None:
        self._engine.put(Record(key, value))

    def batch_put(self, keys: list[bytes], values: list[bytes]) -> None:
        if len(keys) != len(values):
            raise ValueError("keys and values must have the same length!")

        self._engine.batch_put(Record(k, v) for k, v in zip(keys, values))

    def read(self, key: bytes) -> bytes | None:
        return self._engine.read(key)

    def read_key_range(self, start: bytes, end: bytes) -> Iterator[tuple[bytes, bytes]]:
        yield from self._engine.read_key_range(start, end)

    def delete(self, key: bytes) -> None:
        self._engine.delete(key)


def main() -> None:
    with KVStoreAPI() as api:
        server = KVServer(api)
        server.run()


if __name__ == "__main__":
    main()
