from bisect import bisect_right
from pathlib import Path

from kvstore.memtable import MemTable, NOT_FOUND
from kvstore.record import Record, TOMBSTONE


class SSTable:
    INDEX_STRIDE = 128

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.data = open(path, mode="rb")
        self._load_hints()

    @classmethod
    def from_memtable(cls, memtable: MemTable, path: Path | str) -> "SSTable":
        with open(Path(path), mode="ab") as data, open(Path(f"{path}.hint")) as hint:
            offset = 0

            for i, record in enumerate(memtable.records()):
                if i % cls.INDEX_STRIDE == 0:
                    hint.write(
                        len(record.key).to_bytes(4, "big")
                        + offset.to_bytes(8, "big")  # for SSTables larger than 4GB
                        + record.key
                    )

                data.write(record.to_bytes())
                offset += len(record)

        return cls(path)

    def _load_hints(self):
        self.index_keys: list[bytes] = []
        self.index_offsets: list[int] = []

        with open(f"{self.path}.hint", "rb") as file:
            while True:
                header = file.read(12)

                if not header:
                    break

                if len(header) != 12:
                    raise ValueError("corrupt hint file")

                key_size = int.from_bytes(header[:4], "big")
                offset = int.from_bytes(header[4:12], "big")
                key = file.read(key_size)

                if len(key) != key_size:
                    raise ValueError("corrupt hint file")

                self.index_keys.append(key)
                self.index_offsets.append(offset)

    def _find_offset(self, key: bytes) -> int:
        pos = bisect_right(self.index_keys, key) - 1
        return self.index_offsets[pos] if pos >= 0 else 0

    def close(self):
        self.data.close()

    def read(self, key: bytes) -> bytes | None | object:
        self.data.seek(self._find_offset(key))

        while record := Record.from_buffer(self.data):
            if record.key == key:
                return None if record.value is TOMBSTONE else record.value

            if record.key > key:
                return NOT_FOUND

        return NOT_FOUND

    def range(self, start: bytes, end: bytes):
        self.data.seek(self._find_offset(start))

        while record := Record.from_buffer(self.data):
            if record.key >= end:
                break

            if record.key >= start:
                yield record.key, (None if record.value is TOMBSTONE else record.value)
