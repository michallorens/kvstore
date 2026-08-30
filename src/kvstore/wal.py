import logging
from io import BufferedRandom, SEEK_SET
from os import fsync
from typing import Callable, Iterable
from pathlib import Path

from kvstore.record import Record, TOMBSTONE, TOMBSTONE_VALUE_SIZE


class WAL:
    def __init__(
        self,
        wal_dir: str | Path,
        max_wal_size: int | None = None,
        on_rotate: Callable[[int], None] | None = None,
    ) -> None:
        if max_wal_size is not None and max_wal_size <= 0:
            raise ValueError("max_wal_size must be greater than zero")

        self.wal_dir = Path(wal_dir)
        self.max_wal_size = max_wal_size
        self.wal_dir.mkdir(parents=True, exist_ok=True)

        self._current_segment = self._youngest_log_number()
        self._current = self._open_log(self._current_segment)
        self._current_size = self._current.seek(0, SEEK_SET)
        self._on_rotate = on_rotate

    def _should_rotate_wal(self, record_size: int) -> bool:
        return (
            self.max_wal_size is not None
            and self._current_size > 0
            and self._current_size + record_size > self.max_wal_size
        )

    def _youngest_log_number(self) -> int:
        log_numbers = [
            int(path.stem) for path in self.wal_dir.glob("*.log") if path.stem.isdigit()
        ]
        return max(log_numbers, default=0)

    def _open_log(self, log_number: int) -> BufferedRandom:
        return open(self.wal_dir / f"{log_number:06d}.log", mode="a+b")

    def _rotate(self) -> None:
        self._current.flush()
        fsync(self._current.fileno())
        self._current.close()

        if self._on_rotate is not None:
            self._on_rotate(self._current_segment)

        self._current_segment = self._youngest_log_number() + 1
        self._current = self._open_log(self._current_segment)
        self._current_size = self._current.seek(0, SEEK_SET)

    def _write_to_wal(self, record: Record) -> None:
        if record.value is not TOMBSTONE:
            assert isinstance(record.value, bytes)
            if len(record.value) >= TOMBSTONE_VALUE_SIZE:
                raise ValueError("value too long")

        if self._should_rotate_wal(len(record)):
            self._rotate()

        self._current.write(record.to_bytes())
        self._current_size += len(record)

    def append(self, record: Record) -> None:
        self._write_to_wal(record)
        self._current.flush()
        fsync(self._current.fileno())

    def append_batch(self, records: Iterable[Record]) -> None:
        for record in records:
            self._write_to_wal(record)

        self._current.flush()
        fsync(self._current.fileno())

    def _read_wal_file_sequentially(
        self,
        file: BufferedRandom,
        on_read: Callable[[Record], None],
    ):
        file.seek(0, SEEK_SET)

        while True:
            pos = file.tell()

            try:
                record = Record.from_buffer(file)
            except ValueError:
                logging.warning("truncating torn record")
                file.truncate(pos)
                break

            if not record:
                break

            on_read(record)

    def close(self) -> None:
        if (
            hasattr(self, "_current")
            and self._current is not None
            and not self._current.closed
        ):
            self._current.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def replay(self, on_read: Callable[[Record], None], start_segment: int = 0) -> None:
        for file in sorted(
            (
                path
                for path in Path(self.wal_dir).glob("*.log")
                if path.stem.isdigit() and int(path.stem) >= start_segment
            ),
            key=lambda path: int(path.stem),
        ):
            with file.open("r+b") as wal_file:
                self._read_wal_file_sequentially(wal_file, on_read)
