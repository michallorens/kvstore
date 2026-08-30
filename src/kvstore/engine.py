from collections import deque
from threading import RLock
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Iterator

from kvstore.memtable import MemTable, NOT_FOUND
from kvstore.wal import WAL
from kvstore.config import Config
from kvstore.record import Record
from kvstore.sstable import SSTable

STOP_FLUSH_WORKER = object()


class KVStoreEngine:
    def __init__(self, config: Config = Config()) -> None:
        self._config = config
        self.data_dir = Path(config.data_dir)
        self._lock = RLock()
        self.wal = WAL(
            wal_dir=self._config.data_dir,
            max_wal_size=self._config.max_wal_size,
            on_rotate=self._on_wal_rotate,
        )
        self.memtable = MemTable()
        self.frozen_memtables: deque[MemTable] = deque()

        self._flush_queue = Queue()
        self._flush_thread = Thread(
            target=self._flush_worker,
            daemon=True,
        )

    def _on_wal_rotate(self, segment: int) -> None:
        with self._lock:
            frozen = self.memtable
            frozen.freeze()
            self.memtable = MemTable()
            self.frozen_memtables.append(frozen)
            self._flush_queue.put((segment, frozen))

    def _flush_worker(self) -> None:
        while True:
            item = self._flush_queue.get()

            try:
                if item is STOP_FLUSH_WORKER:
                    break

                segment, frozen = item

                sstable = SSTable.from_memtable(
                    frozen,
                    Path(self.data_dir) / f"{segment:06d}.sst",
                )

                with self._lock:
                    self.sstables.append(sstable)
                    self.frozen_memtables.remove(frozen)
            finally:
                self._flush_queue.task_done()

    def _next_wal_segment(self) -> int:
        if len(self.sstables) == 0:
            return 0
        return int(self.sstables[-1].path.stem) + 1

    def open(self) -> "KVStoreEngine":
        self._flush_thread.start()
        self.sstables: deque[SSTable] = deque(
            SSTable(path) for path in sorted(self.data_dir.glob("*.sst"))
        )
        self.wal.open()
        self.wal.replay(
            on_read=self.memtable.put, start_segment=self._next_wal_segment()
        )
        return self

    def __enter__(self) -> "KVStoreEngine":
        return self.open()

    def close(self) -> None:
        self._flush_queue.put(STOP_FLUSH_WORKER)
        self.wal.close()
        for sstable in self.sstables:
            sstable.close()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def put(self, record: Record):
        with self._lock:
            self.wal.append(record)
            self.memtable.put(record)

    def _append_to_current_memtable(self, record: Record) -> None:
        self.memtable.put(record)

    def batch_put(self, records: Iterator[Record]):
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
