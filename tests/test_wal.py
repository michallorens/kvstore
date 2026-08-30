from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from kvstore.wal import WAL
from kvstore.record import Record


class TestWAL(TestCase):
    def test_should_rotate_wal(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal = WAL(wal_dir, max_wal_size=20)
            self.assertFalse(wal._should_rotate_wal(20))
            self.assertFalse(wal._should_rotate_wal(21))
            wal.append(Record(b"key", b"value"))
            self.assertTrue(wal._should_rotate_wal(1))
            wal._current.close()

    def test_youngest_log_number(self) -> None:
        with TemporaryDirectory() as wal_dir:
            Path(wal_dir, "000000.log").touch()
            Path(wal_dir, "000001.log").touch()

            wal = WAL(wal_dir)
            self.assertEqual(wal._youngest_log_number(), 1)
            wal._current.close()

    def test_rotate(self) -> None:
        with TemporaryDirectory() as wal_dir:
            Path(wal_dir, "000000.log").touch()

            wal = WAL(wal_dir)
            wal._rotate()

            self.assertEqual(Path(wal._current.name).name, "000001.log")
            self.assertTrue(Path(wal_dir, "000001.log").exists())
            wal._current.close()

    def test_write_to_wal_and_rotate(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal = WAL(wal_dir, max_wal_size=20)
            wal.append(Record(b"key", b"value"))
            self.assertEqual(wal._current_size, 20)

            wal.append(Record(b"next", b"value"))

            self.assertEqual(Path(wal._current.name).name, "000001.log")
            self.assertEqual(wal._current_size, 21)
            self.assertEqual(Path(wal_dir, "000000.log").stat().st_size, 20)
            self.assertEqual(Path(wal_dir, "000001.log").stat().st_size, 21)
            wal._current.close()

    def test_read_wal_file_sequentially(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal = WAL(wal_dir)
            wal.append(Record(b"first", b"value"))
            wal.append(Record(b"next", b"value"))
            wal.append(Record(b"last", b"value"))

            records = []

            def on_read(record: Record) -> None:
                records.append(record)

            wal._read_wal_file_sequentially(wal._current, on_read=on_read)

            self.assertEqual(len(records), 3)
            self.assertEqual(records[0], Record(b"first", b"value"))
            self.assertEqual(records[1], Record(b"next", b"value"))
            self.assertEqual(records[2], Record(b"last", b"value"))
            wal._current.close()

    def test_replay(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal = WAL(wal_dir, max_wal_size=20)
            wal.append(Record(b"first", b"value"))
            wal.append(Record(b"next", b"value"))

            records = []
            wal.replay(on_read=records.append)

            self.assertEqual(len(records), 2)
            self.assertEqual(records[0], Record(b"first", b"value"))
            self.assertEqual(records[1], Record(b"next", b"value"))
            wal._current.close()

    def test_replay_from_specified_segment(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal = WAL(wal_dir, max_wal_size=20)
            wal.append(Record(b"first", b"value"))
            wal.append(Record(b"next", b"value"))

            records = []
            wal.replay(on_read=records.append, start_segment=1)

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0], Record(b"next", b"value"))
            wal._current.close()

    def test_replay_ignores_torn_record_at_end_of_log(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal = WAL(wal_dir)
            wal.append(Record(b"first", b"value"))

            wal._current.write(b"\x00\x00\x00\x03\x00\x00\x00")
            wal._current.flush()
            wal._current.close()

            records = []
            wal.replay(on_read=records.append)

            self.assertEqual(records, [Record(b"first", b"value")])
            self.assertEqual(
                Path(wal_dir, "000000.log").stat().st_size,
                len(Record(b"first", b"value").to_bytes()),
            )
