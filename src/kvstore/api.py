from collections import deque
from threading import RLock

from kvstore.memtable import MemTable, NOT_FOUND
from kvstore.wal import WAL
from kvstore.config import Config
from kvstore.record import Record


class KVStoreAPI:
    def __init__(self, config: Config = Config()) -> None:
        self._lock = RLock()
        self.memtable = MemTable()
        self.frozen_memtables: deque[MemTable] = deque()

        def on_wal_rotate(segment: int) -> None:
            with self._lock:
                frozen = self.memtable
                frozen.freeze()
                self.memtable = MemTable()
                self.frozen_memtables.append(frozen)

            # TODO schedule flush

        self.wal = WAL(
            wal_dir=config.wal_dir,
            max_wal_size=config.max_wal_size,
            on_rotate=on_wal_rotate,
        )

        self.wal.replay(on_put=self.memtable.put)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.wal.current.close()

    def put(self, key: bytes, value: bytes):
        record = Record(key, value)

        with self._lock:
            self.wal.append(record)
            self.memtable.put(record)

    def batch_put(self, keys: list[bytes], values: list[bytes]):
        if len(keys) != len(values):
            raise ValueError("keys and values must have the same length!")

        with self._lock:
            records = (Record(k, v) for k, v in zip(keys, values))
            self.wal.append_batch(records)
            for record in records:
                self.memtable.put(record)

    def _get_memtables(self) -> list[MemTable]:
        with self._lock:
            return [*self.frozen_memtables, self.memtable]

    def read(self, key: bytes) -> bytes | None:
        for memtable in reversed(self._get_memtables()):
            value = memtable.read(key)

            if value is not NOT_FOUND:
                return value  # ty: ignore

        return None

    def read_key_range(self, start: bytes, end: bytes) -> dict[bytes, bytes]:
        result: dict[bytes, bytes | None] = {}

        for memtable in self._get_memtables():
            result.update(memtable.range(start, end))

        return {key: value for key, value in result.items() if value is not None}

    def delete(self, key: bytes) -> None:
        record = Record.tombstone(key)
        self.wal.append(record)
        self.memtable.put(record)
