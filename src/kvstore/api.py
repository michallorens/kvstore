from kvstore.keydir import KeyDir, TOMBSTONE_VALUE_SIZE
from kvstore.wal import WAL
from kvstore.config import Config


class KVStoreAPI:
    def __init__(self, config: Config = Config()) -> None:
        self.wal = WAL(
            wal_dir=config.wal_dir,
            max_wal_size=config.max_wal_size,
        )
        self.keydir = KeyDir(wal_dir=self.wal.wal_dir)
        self.wal.replay(
            on_put=self.keydir.add,
            on_delete=self.keydir.delete,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.wal.current.close()
        self.keydir.close()

    def put(self, key: bytes, value: bytes):
        entry = self.wal.append(key, value)
        self.keydir.add(key, entry)

    def batch_put(self, keys: list[bytes], values: list[bytes]):
        if len(keys) != len(values):
            raise ValueError("keys and values must have the same length!")

        key_dir_entries = self.wal.append_batch(zip(keys, values))
        self.keydir.keydir |= key_dir_entries

    def read(self, key: bytes) -> bytes | None:
        return self.keydir.get(key)

    def read_key_range(self, start: bytes, end: bytes):
        results = {}

        for file in sorted(
            (path for path in self.wal.wal_dir.glob("*.log") if path.stem.isdigit()),
            key=lambda path: int(path.stem),
        ):
            with file.open("rb") as wal_file:
                while True:
                    header = wal_file.read(12)

                    if not header:
                        break

                    if len(header) < 12:
                        break

                    key_size = int.from_bytes(header[4:8])
                    value_size = int.from_bytes(header[8:])
                    key = wal_file.read(key_size)
                    value = (
                        b""
                        if value_size == TOMBSTONE_VALUE_SIZE
                        else wal_file.read(value_size)
                    )

                    if len(key) != key_size or (
                        value_size != TOMBSTONE_VALUE_SIZE and len(value) != value_size
                    ):
                        break

                    if start <= key < end:
                        if value_size == TOMBSTONE_VALUE_SIZE:
                            results.pop(key, None)
                        else:
                            results[key] = value

        return results

    def delete(self, key: bytes) -> None:
        self.wal.append_tombstone(key)
        self.keydir.delete(key)
