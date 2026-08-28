from dataclasses import dataclass
from io import BufferedRandom, BufferedReader, SEEK_SET
from pathlib import Path
from zlib import crc32

TOMBSTONE_VALUE_SIZE = (1 << 32) - 1


@dataclass
class KeyDirEntry:
    segment: int
    offset: int
    value_size: int


class KeyDir:
    keydir: dict[bytes, KeyDirEntry]
    wal_files: dict[str, BufferedReader]

    def __init__(self, wal_dir: Path, replay: bool = True):
        self.keydir = {}
        self.wal_files = {}
        self.wal_dir = wal_dir
        if replay:
            self._cache_wal_files()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return self.close()

    def _get_or_open_wal_file(self, path: Path) -> BufferedReader:
        if path.name in self.wal_files.keys():
            return self.wal_files[path.name]
        else:
            wal_file = open(path, mode="rb")
            self.wal_files[path.name] = wal_file
            return wal_file

    def close(self):
        for wal_file in self.wal_files.values():
            wal_file.close()

    def get(self, key: bytes) -> bytes | None:
        if key not in self.keydir.keys():
            return None
        else:
            entry = self.keydir[key]
            file = self._get_or_open_wal_file(self.wal_dir / f"{entry.segment:06d}.log")
            file.seek(entry.offset, SEEK_SET)
            return file.read(entry.value_size)

    def add(self, key: bytes, entry: KeyDirEntry):
        self.keydir[key] = entry

    def delete(self, key: bytes):
        self.keydir.pop(key)

    def _cache_wal_file_entries(self, file: BufferedRandom):
        file.seek(0, SEEK_SET)

        while True:
            pos = file.tell()
            header = file.read(12)

            if not header:
                break

            if len(header) < 12:
                file.truncate(pos)
                break

            crc = header[:4]
            key_size = int.from_bytes(header[4:8])
            value_size = int.from_bytes(header[8:])

            if not key_size:
                file.truncate(pos)
                break

            key = file.read(key_size)
            offset = file.tell()
            value = b"" if value_size == TOMBSTONE_VALUE_SIZE else file.read(value_size)

            if (
                len(key) != key_size
                or (value_size != TOMBSTONE_VALUE_SIZE and len(value) != value_size)
                or crc != crc32(header[4:12] + key + value).to_bytes(4)
            ):
                file.truncate(pos)
                break

            if value_size == TOMBSTONE_VALUE_SIZE:
                self.keydir.pop(key, None)
            else:
                self.keydir[key] = KeyDirEntry(
                    segment=int(Path(file.name).stem),
                    offset=offset,
                    value_size=value_size,
                )

    def _cache_wal_files(self) -> bytes | None:
        log_files = sorted(
            (path for path in Path(self.wal_dir).glob("*.log") if path.stem.isdigit()),
            key=lambda path: int(path.stem),
        )

        for log_file in log_files:
            with log_file.open("r+b") as file:
                self._cache_wal_file_entries(file)
