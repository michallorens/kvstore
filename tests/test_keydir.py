from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

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

    def test_caches_entries_from_all_segments_and_latest_wins(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal_path = Path(wal_dir)
            self._write_records(wal_path / "000001.log", [(b"old", b"one")])
            self._write_records(
                wal_path / "000002.log",
                [(b"old", b"two"), (b"new", b"three")],
            )

            with KeyDir(wal_path) as keydir:
                self.assertEqual(keydir.get(b"old"), b"two")
                self.assertEqual(keydir.get(b"new"), b"three")

    def test_empty_wal_directory_starts_with_empty_index(self) -> None:
        with TemporaryDirectory() as wal_dir:
            with KeyDir(Path(wal_dir)) as keydir:
                self.assertEqual(keydir.keydir, {})

    @staticmethod
    def _write_records(path: Path, records: list[tuple[bytes, bytes]]) -> None:
        with path.open("wb") as file:
            for key, value in records:
                file.write(len(key).to_bytes(4))
                file.write(len(value).to_bytes(4))
                file.write(key)
                file.write(value)
