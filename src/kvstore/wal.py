import logging
from io import BufferedRandom, SEEK_SET
from os import fsync
from typing import Callable, Iterable
from pathlib import Path

from kvstore.record import Record


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
        self.current_segment = self._youngest_log_number()
        self.current = self._open_log(self.current_segment)
        self.current_size = self.current.seek(0, SEEK_SET)
        self.on_rotate = on_rotate

    def _should_rotate_wal(self, record_size: int) -> bool:
        return (
            self.max_wal_size is not None
            and self.current_size > 0
            and self.current_size + record_size > self.max_wal_size
        )

    def _youngest_log_number(self) -> int:
        log_numbers = [
            int(path.stem) for path in self.wal_dir.glob("*.log") if path.stem.isdigit()
        ]
        return max(log_numbers, default=0)

    def _open_log(self, log_number: int) -> BufferedRandom:
        return open(self.wal_dir / f"{log_number:06d}.log", mode="a+b")

    def _rotate(self) -> None:
        self.current.flush()
        fsync(self.current.fileno())
        self.current.close()

        if self.on_rotate is not None:
            self.on_rotate(self.current_segment)

        self.current_segment = self._youngest_log_number() + 1
        self.current = self._open_log(self.current_segment)
        self.current_size = self.current.seek(0, SEEK_SET)

    def _write_to_wal(self, record: Record) -> None:
        # if record.value is not TOMBSTONE and len(record.value) >= TOMBSTONE_VALUE_SIZE:
        #     raise ValueError("value too long")

        if self._should_rotate_wal(len(record)):
            self._rotate()

        self.current.write(record.to_bytes())
        self.current_size += len(record)

    def append(self, record: Record) -> None:
        self._write_to_wal(record)
        self.current.flush()
        fsync(self.current.fileno())

    def append_batch(self, records: Iterable[Record]) -> None:
        for record in records:
            self._write_to_wal(record)

        self.current.flush()
        fsync(self.current.fileno())

    def _read_wal_file_sequentially(
        self,
        file: BufferedRandom,
        on_put: Callable[[Record], None],
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

            on_put(record)

    def replay(self, on_put: Callable[[Record], None]) -> None:
        for file in sorted(
            (path for path in Path(self.wal_dir).glob("*.log") if path.stem.isdigit()),
            key=lambda path: int(path.stem),
        ):
            with file.open("r+b") as wal_file:
                self._read_wal_file_sequentially(wal_file, on_put)
