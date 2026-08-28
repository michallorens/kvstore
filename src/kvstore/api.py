from kvstore.keydir import KeyDir
from kvstore.wal import WAL
from kvstore.config import Config


class KVStoreAPI:
    def __init__(self, config: Config = Config()) -> None:
        self.wal = WAL(
            wal_dir=config.wal_dir,
            max_wal_size=config.max_wal_size,
        )
        self.keydir = KeyDir(wal_dir=self.wal.wal_dir)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.wal.current.close()
        self.keydir.close()

    def put(self, key: bytes, value: bytes):
        entry = self.wal.append(key, value)
        self.keydir.add(key, entry)

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
                    value = wal_file.read(value_size)

                    if len(key) != key_size or len(value) != value_size:
                        break

                    if start <= key < end:
                        results[key] = value

        return results

    def delete(self, key: bytes) -> None:
        self.wal.append(key, b"")
