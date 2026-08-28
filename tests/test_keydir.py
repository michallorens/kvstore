from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from zlib import crc32

from kvstore.keydir import KeyDir, KeyDirEntry


class TestKeyDir(TestCase):
    def test_get_returns_none_for_missing_key(self) -> None:
        with TemporaryDirectory() as wal_dir:
            with KeyDir(Path(wal_dir)) as keydir:
                self.assertIsNone(keydir.get(b"missing"))

    def test_add_indexes_value(self) -> None:
        with TemporaryDirectory() as wal_dir:
            log_file = Path(wal_dir, "000001.log")
            log_file.write_bytes(b"value")

            with KeyDir(Path(wal_dir)) as keydir:
                keydir.add(b"key", KeyDirEntry(1, 0, 5))

                self.assertEqual(keydir.get(b"key"), b"value")

    def test_add_replaces_existing_entry(self) -> None:
        with TemporaryDirectory() as wal_dir:
            log_file = Path(wal_dir, "000001.log")
            log_file.write_bytes(b"oldnew")

            with KeyDir(Path(wal_dir)) as keydir:
                keydir.add(b"key", KeyDirEntry(1, 0, 3))
                keydir.add(b"key", KeyDirEntry(1, 3, 3))

                self.assertEqual(keydir.get(b"key"), b"new")

    def test_empty_wal_directory_starts_with_empty_index(self) -> None:
        with TemporaryDirectory() as wal_dir:
            with KeyDir(Path(wal_dir)) as keydir:
                self.assertEqual(keydir.keydir, {})

    @staticmethod
    def _write_records(path: Path, records: list[tuple[bytes, bytes]]) -> None:
        with path.open("wb") as file:
            for key, value in records:
                key_size = len(key).to_bytes(4)
                value_size = len(value).to_bytes(4)
                crc = crc32(key_size + value_size + key + value).to_bytes(4)

                file.write(crc)
                file.write(key_size)
                file.write(value_size)
                file.write(key)
                file.write(value)
