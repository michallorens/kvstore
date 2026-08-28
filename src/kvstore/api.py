from io import BufferedReader
from os import SEEK_CUR, SEEK_END
from pathlib import Path

from kvstore.wal import WAL
from kvstore.config import Config


def find_in_file(key: bytes, file: BufferedReader) -> bytes | None:
    file.seek(0, SEEK_END)

    while file.tell() >= 8:
        file.seek(-8, SEEK_CUR)
        key_size = int.from_bytes(file.read(4))
        value_size = int.from_bytes(file.read(4))
        record_size = key_size + value_size + 8

        if file.tell() < record_size:
            return None

        file.seek(-record_size, SEEK_CUR)
        if file.read(key_size) == key:
            return file.read(value_size)

        file.seek(-key_size, SEEK_CUR)

    return None


def find_in_wal(key: bytes, wal_dir: str | Path) -> bytes | None:
    log_files = sorted(
        (path for path in Path(wal_dir).glob("*.log") if path.stem.isdigit()),
        key=lambda path: int(path.stem),
        reverse=True,
    )

    for log_file in log_files:
        with log_file.open("rb") as file:
            value = find_in_file(key, file)
            if value is not None:
                return value

    return None


class KVStoreAPI:
    def __init__(self, config: Config = Config()) -> None:
        self.wal = WAL(
            wal_dir=config.wal_dir,
            max_wal_size=config.max_wal_size,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.wal.current.close()

    def put(self, key: bytes, value: bytes):
        self.wal.append(key, value)

    def read(self, key: bytes) -> bytes | None:
        return find_in_wal(key, self.wal.wal_dir)

    def delete(self, key: bytes) -> None:
        self.wal.append(key, b"")
