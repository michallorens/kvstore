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

    def delete(self, key: bytes) -> None:
        self.wal.append(key, b"")
