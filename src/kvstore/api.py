from kvstore.memtable import MemTable
from kvstore.keydir import KeyDir, KeyDirEntry
from kvstore.wal import WAL
from kvstore.config import Config


class KVStoreAPI:
    def __init__(self, config: Config = Config()) -> None:
        self.wal = WAL(
            wal_dir=config.wal_dir,
            max_wal_size=config.max_wal_size,
        )
        self.keydir = KeyDir(wal_dir=self.wal.wal_dir)
        self.memtable = MemTable()

        def on_put(key: bytes, value: bytes, entry: KeyDirEntry):
            self.keydir.add(key, entry)
            self.memtable.put(key, value)

        def on_delete(key: bytes):
            self.keydir.delete(key)
            self.memtable.delete(key)

        self.wal.replay(
            on_put=on_put,
            on_delete=on_delete,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.wal.current.close()
        self.keydir.close()

    def put(self, key: bytes, value: bytes):
        entry = self.wal.append(key, value)
        self.keydir.add(key, entry)
        self.memtable.put(key, value)

    def batch_put(self, keys: list[bytes], values: list[bytes]):
        if len(keys) != len(values):
            raise ValueError("keys and values must have the same length!")

        key_dir_entries = self.wal.append_batch(zip(keys, values))
        self.keydir.keydir |= key_dir_entries
        for key, value in zip(keys, values):
            self.memtable.put(key, value)

    def read(self, key: bytes) -> bytes | None:
        return self.memtable.read(key)

    def read_key_range(self, start: bytes, end: bytes):
        return self.memtable.range(start, end)

    def delete(self, key: bytes) -> None:
        self.wal.append_tombstone(key)
        self.keydir.delete(key)
        self.memtable.delete(key)
