from dataclasses import dataclass
from io import BufferedReader, SEEK_SET
from pathlib import Path

TOMBSTONE_VALUE_SIZE = (1 << 32) - 1


@dataclass
class KeyDirEntry:
    segment: int
    offset: int
    value_size: int


class KeyDir:
    keydir: dict[bytes, KeyDirEntry]
    wal_files: dict[str, BufferedReader]

    def __init__(self, wal_dir: Path):
        self.keydir = {}
        self.wal_files = {}
        self.wal_dir = wal_dir

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
