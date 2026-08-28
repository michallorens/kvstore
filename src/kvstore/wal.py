from io import BufferedRandom, SEEK_SET
from os import fsync
from typing import Iterable
from pathlib import Path
from zlib import crc32

from kvstore.keydir import KeyDirEntry, TOMBSTONE_VALUE_SIZE


class WAL:
    def __init__(self, wal_dir: str | Path, max_wal_size: int | None = None) -> None:
        if max_wal_size is not None and max_wal_size <= 0:
            raise ValueError("max_wal_size must be greater than zero")

        self.wal_dir = Path(wal_dir)
        self.max_wal_size = max_wal_size
        self.wal_dir.mkdir(parents=True, exist_ok=True)
        self.current_segment = self._youngest_log_number()
        self.current = self._open_log(self.current_segment)
        self.current_size = self.current.seek(0, SEEK_SET)

    def _calculate_record_checksum(
        self, key_size: bytes, value_size: bytes, key: bytes, value: bytes
    ) -> bytes:
        return crc32(key_size + value_size + key + value).to_bytes(4)

    def _calculate_record_size(self, key: bytes, value: bytes) -> int:
        return len(key) + len(value) + 12

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
        self.current_segment = self._youngest_log_number() + 1
        self.current = self._open_log(self.current_segment)
        self.current_size = self.current.seek(0, SEEK_SET)

    def _write_to_wal(
        self, key_size: bytes, value_size: bytes, key: bytes, value: bytes
    ) -> int:
        record_size = self._calculate_record_size(key, value)
        if self._should_rotate_wal(record_size):
            self._rotate()

        self.current.write(
            self._calculate_record_checksum(
                key_size=key_size,
                value_size=value_size,
                key=key,
                value=value,
            )
            + key_size
            + value_size
            + key
            + value
        )

        self.current_size += record_size
        return self.current_size - len(value)

    def append(self, key: bytes, value: bytes) -> KeyDirEntry:
        offset = self._write_to_wal(
            key_size=len(key).to_bytes(4),
            value_size=len(value).to_bytes(4),
            key=key,
            value=value,
        )

        self.current.flush()
        fsync(self.current.fileno())

        return KeyDirEntry(
            segment=self.current_segment, offset=offset, value_size=len(value)
        )

    def append_batch(
        self, items: Iterable[tuple[bytes, bytes]]
    ) -> dict[bytes, KeyDirEntry]:
        key_dir_entries = {}

        for key, value in items:
            offset = self._write_to_wal(
                key_size=len(key).to_bytes(4),
                value_size=len(value).to_bytes(4),
                key=key,
                value=value,
            )

            key_dir_entries[key] = KeyDirEntry(
                segment=self.current_segment, offset=offset, value_size=len(value)
            )

        self.current.flush()
        fsync(self.current.fileno())

        return key_dir_entries

    def append_tombstone(self, key: bytes):
        self._write_to_wal(
            key_size=len(key).to_bytes(4),
            value_size=TOMBSTONE_VALUE_SIZE.to_bytes(4),
            key=key,
            value=b"",
        )

        self.current.flush()
        fsync(self.current.fileno())
