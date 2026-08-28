from dataclasses import dataclass
from io import BufferedReader, SEEK_CUR, SEEK_SET
from pathlib import Path


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

    def _cache_wal_file_entries(self, file: BufferedReader):
        file.seek(0, SEEK_SET)

        while True:
            key_size = int.from_bytes(file.read(4))
            value_size = int.from_bytes(file.read(4))

            if not key_size or not value_size:
                break

            key = file.read(key_size)
            self.keydir[key] = KeyDirEntry(
                segment=int(Path(file.name).stem),
                offset=file.tell(),
                value_size=value_size,
            )

            file.seek(value_size, SEEK_CUR)

    def _cache_wal_files(self) -> bytes | None:
        log_files = sorted(
            (path for path in Path(self.wal_dir).glob("*.log") if path.stem.isdigit()),
            key=lambda path: int(path.stem),
        )

        for log_file in log_files:
            with log_file.open("rb") as file:
                self._cache_wal_file_entries(file)
