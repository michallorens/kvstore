from io import BufferedRandom, SEEK_SET
from pathlib import Path
from zlib import crc32

from kvstore.keydir import KeyDirEntry


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

    def append(self, key: bytes, value: bytes) -> KeyDirEntry:
        record_size = len(key) + len(value) + 12
        if (
            self.max_wal_size is not None
            and self.current_size > 0
            and self.current_size + record_size > self.max_wal_size
        ):
            self._rotate()

        key_size = len(key).to_bytes(4)
        value_size = len(value).to_bytes(4)
        crc = crc32(key_size + value_size + key + value).to_bytes(4)

        self.current.write(crc)
        self.current.write(key_size)
        self.current.write(value_size)
        self.current.write(key)

        offset = self.current.tell()

        self.current.write(value)
        self.current_size += record_size
        self.current.flush()

        return KeyDirEntry(
            segment=self.current_segment, offset=offset, value_size=len(value)
        )

    def _rotate(self) -> None:
        self.current.close()
        self.current_segment = self._youngest_log_number() + 1
        self.current = self._open_log(self.current_segment)
        self.current_size = self.current.seek(0, SEEK_SET)

    def _youngest_log_number(self) -> int:
        log_numbers = [
            int(path.stem) for path in self.wal_dir.glob("*.log") if path.stem.isdigit()
        ]
        return max(log_numbers, default=0)

    def _open_log(self, log_number: int) -> BufferedRandom:
        return open(self.wal_dir / f"{log_number:06d}.log", mode="a+b")
