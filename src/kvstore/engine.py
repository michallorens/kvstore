from collections import deque
from threading import RLock
from pathlib import Path

from kvstore.memtable import MemTable, NOT_FOUND
from kvstore.wal import WAL
from kvstore.config import Config
from kvstore.record import Record
from kvstore.sstable import SSTable


class KVStoreEngine:
    def __init__(self, config: Config = Config()) -> None:
        self.data_dir = Path(config.data_dir)
        self._lock = RLock()
        self.memtable = MemTable()
        self.sstables: deque[SSTable] = deque(
            SSTable(path) for path in sorted(self.data_dir.glob("*.sst"))
        )
        self.frozen_memtables: deque[MemTable] = deque()

        self.wal = WAL(
            wal_dir=config.data_dir,
            max_wal_size=config.max_wal_size,
            on_rotate=self._on_wal_rotate,
        )

        self.wal.replay(
            on_read=self.memtable.put, start_segment=self._next_wal_segment()
        )

    def _on_wal_rotate(self, segment: int) -> None:
        with self._lock:
            frozen = self.memtable
            frozen.freeze()
            self.memtable = MemTable()
            self.frozen_memtables.append(frozen)

        sstable = SSTable.from_memtable(
            frozen, Path(self.data_dir) / f"{segment:06d}.sst"
        )

        with self._lock:
            self.sstables.append(sstable)
            self.frozen_memtables.popleft()

    def _next_wal_segment(self) -> int:
        if len(self.sstables) == 0:
            return 0
        return int(self.sstables[-1].path.stem) + 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.wal.close()
        for sstable in self.sstables:
            sstable.close()

    def put(self, key: bytes, value: bytes):
        record = Record(key, value)

        with self._lock:
            self.wal.append(record)
            self.memtable.put(record)

    def _append_to_current_memtable(self, record: Record) -> None:
        self.memtable.put(record)

    def batch_put(self, keys: list[bytes], values: list[bytes]):
        if len(keys) != len(values):
            raise ValueError("keys and values must have the same length!")

        records = [Record(k, v) for k, v in zip(keys, values)]

        with self._lock:
            self.wal.append_batch(records, on_write=self._append_to_current_memtable)

    def delete(self, key: bytes) -> None:
        with self._lock:
            record = Record.tombstone(key)
            self.wal.append(record)
            self.memtable.put(record)

    def _get_tables(self) -> list[MemTable | SSTable]:
        with self._lock:
            return [*self.sstables, *self.frozen_memtables, self.memtable]

    def read(self, key: bytes) -> bytes | None:
        for memtable in reversed(self._get_tables()):
            value = memtable.read(key)

            if value is not NOT_FOUND:
                if value is None:
                    return None
                assert isinstance(value, bytes)
                return value

        return None

    def read_key_range(self, start: bytes, end: bytes) -> dict[bytes, bytes]:
        result: dict[bytes, bytes | None] = {}

        for memtable in self._get_tables():
            result.update(memtable.range(start, end))

        return {key: value for key, value in result.items() if value is not None}
