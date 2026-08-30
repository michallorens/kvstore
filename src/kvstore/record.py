from dataclasses import dataclass
from typing import Optional
from io import BufferedIOBase
from zlib import crc32

TOMBSTONE = object()
TOMBSTONE_VALUE_SIZE = (1 << 32) - 1


@dataclass
class Record:
    key: bytes
    value: bytes | object

    @classmethod
    def tombstone(cls, key: bytes) -> "Record":
        return cls(key, TOMBSTONE)

    @classmethod
    def _parse_header(cls, header: bytes) -> tuple[int, int, bytes]:
        crc = header[:4]
        key_size = int.from_bytes(header[4:8], signed=False)
        value_size = int.from_bytes(header[8:12], signed=False)

        return key_size, value_size, crc

    @classmethod
    def _validate(
        cls,
        header: bytes,
        key: bytes,
        value: bytes,
    ) -> None:
        key_size, value_size, crc = cls._parse_header(header)

        if not (
            len(header) == 12
            and len(key) == key_size
            and (value_size == TOMBSTONE_VALUE_SIZE or len(value) == value_size)
            and crc == crc32(header[4:12] + key + value).to_bytes(4, "big")
        ):
            raise ValueError("record malformed")

    @classmethod
    def from_buffer(cls, buffer: BufferedIOBase) -> Optional["Record"]:
        header = buffer.read(12)

        if not header:
            return

        key_size, value_size, _ = cls._parse_header(header)
        key = buffer.read(key_size)

        if value_size == TOMBSTONE_VALUE_SIZE:
            cls._validate(header, key, b"")
            return cls.tombstone(key)
        else:
            value = buffer.read(value_size)
            cls._validate(header, key, value)
            return cls(key, value)

    def __len__(self) -> int:
        return len(self.key) + len(self._get_value()) + 12

    def _get_value(self) -> bytes:
        if self.value is TOMBSTONE:
            return b""

        assert isinstance(self.value, bytes)
        return self.value

    def _get_value_size(self) -> int:
        if self.value is TOMBSTONE:
            return TOMBSTONE_VALUE_SIZE

        assert isinstance(self.value, bytes)
        return len(self.value)

    def _get_bytes(self) -> bytes:
        return (
            len(self.key).to_bytes(4, "big")
            + self._get_value_size().to_bytes(4, "big")
            + self.key
            + self._get_value()
        )

    def _get_checksum(self) -> bytes:
        return crc32(self._get_bytes()).to_bytes(4, "big")

    def to_bytes(self) -> bytes:
        return self._get_checksum() + self._get_bytes()
