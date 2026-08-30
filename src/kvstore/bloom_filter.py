import hashlib
import math
import os
from io import BufferedIOBase
from pathlib import Path


class BloomFilter:
    def __init__(self, capacity: int, false_positive_rate: float = 0.01):
        self.capacity = capacity
        self.false_positive_rate = false_positive_rate

        self.num_bits = math.ceil(
            -capacity * math.log(false_positive_rate) / (math.log(2) ** 2)
        )

        self.num_hashes = max(
            1,
            round(self.num_bits / capacity * math.log(2)),
        )

        self.bits = bytearray((self.num_bits + 7) // 8)

    def _hashes(self, key: bytes):
        digest = hashlib.sha256(key).digest()

        h1 = int.from_bytes(digest[:8], "little")
        h2 = int.from_bytes(digest[8:16], "little")

        for i in range(self.num_hashes):
            yield (h1 + i * h2) % self.num_bits

    def add(self, key: bytes) -> None:
        for index in self._hashes(key):
            self.bits[index // 8] |= 1 << (index % 8)

    def might_contain(self, key: bytes) -> bool:
        for index in self._hashes(key):
            if not (self.bits[index // 8] & (1 << (index % 8))):
                return False

        return True

    def write_to(self, file: BufferedIOBase) -> None:
        file.write(self.num_bits.to_bytes(8, "big"))
        file.write(self.num_hashes.to_bytes(4, "big"))
        file.write(self.bits)

        file.flush()
        os.fsync(file.fileno())

    @classmethod
    def from_file(cls, path: Path) -> "BloomFilter":
        with path.open("rb") as file:
            num_bits = int.from_bytes(file.read(8), "big")
            num_hashes = int.from_bytes(file.read(4), "big")
            bits = file.read()

            bloom = cls.__new__(cls)
            bloom.num_bits = num_bits
            bloom.num_hashes = num_hashes
            bloom.bits = bytearray(bits)

            return bloom
