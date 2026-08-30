from kvstore.engine import KVStoreEngine
from kvstore.server import KVServer


# class KVStore:
#     def __init__(self, config: Config = Config()) -> None:
#         self._engine = KVStoreEngine(config)

#     def put(self, key: bytes, value: bytes) -> None:
#         self._engine.put(Record(key, value))

#     def batch_put(self, keys: list[bytes], values: list[bytes]) -> None:
#         if len(keys) != len(values):
#             raise ValueError(...)

#         self._engine.put_batch(Record(k, v) for k, v in zip(keys, values))

#     def read(self, key: bytes) -> bytes | None:
#         return self._engine.read(key)

#     def read_key_range(self, start: bytes, end: bytes) -> dict[bytes, bytes]:
#         return self._engine.read_range(start, end)

#     def delete(self, key: bytes) -> None:
#         self._engine.delete(key)


def main() -> None:
    with KVStoreEngine() as store:
        server = KVServer(store)
        server.run()


if __name__ == "__main__":
    main()
