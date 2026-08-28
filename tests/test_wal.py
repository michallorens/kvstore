from io import SEEK_SET
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from zlib import crc32

from kvstore.wal import WAL


class TestWAL(TestCase):
    def test_appends_crc_for_record_contents(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal = WAL(wal_dir)
            wal.append(b"key", b"value")
            wal.current.seek(0, SEEK_SET)

            self.assertEqual(
                int.from_bytes(wal.current.read(4)),
                crc32((3).to_bytes(4) + (5).to_bytes(4) + b"keyvalue"),
            )
            wal.current.close()

    def test_opens_youngest_log_and_rotates(self) -> None:
        with TemporaryDirectory() as wal_dir:
            Path(wal_dir, "000003.log").touch()
            Path(wal_dir, "000001.log").touch()

            wal = WAL(wal_dir)
            self.assertEqual(Path(wal.current.name).name, "000003.log")

            wal._rotate()
            self.assertEqual(Path(wal.current.name).name, "000004.log")
            self.assertTrue(Path(wal_dir, "000004.log").exists())
            wal.current.close()

    def test_rotates_before_record_exceeds_max_size(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal = WAL(wal_dir, max_wal_size=20)
            wal.append(b"key", b"value")
            self.assertEqual(wal.current_size, 20)

            wal.append(b"next", b"value")

            self.assertEqual(Path(wal.current.name).name, "000001.log")
            self.assertEqual(wal.current_size, 21)
            self.assertEqual(Path(wal_dir, "000000.log").stat().st_size, 20)
            self.assertEqual(Path(wal_dir, "000001.log").stat().st_size, 21)
            wal.current.close()

    def test_allows_single_record_larger_than_max_size(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal = WAL(wal_dir, max_wal_size=8)
            wal.append(b"key", b"value")

            self.assertEqual(Path(wal.current.name).name, "000000.log")
            self.assertEqual(wal.current_size, 20)
            wal.current.close()
