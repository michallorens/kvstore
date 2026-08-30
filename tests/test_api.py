from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from kvstore.engine import KVStoreEngine
from kvstore.config import Config
from kvstore.wal import WAL
from kvstore.record import Record
from kvstore.sstable import SSTable


class TestAPI(TestCase):
    def test_replays_entries_from_all_segments_and_latest_wins(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal = WAL(wal_dir, max_wal_size=18)
            try:
                wal.append(Record(b"old", b"one"))
                wal.append(Record(b"old", b"two"))
                wal.append(Record(b"new", b"three"))
            finally:
                wal._current.close()

            with KVStoreEngine(Config(data_dir=wal_dir, max_wal_size=18)) as store:
                self.assertEqual(store.read(b"old"), b"two")
                self.assertEqual(store.read(b"new"), b"three")

    def test_batch_put_updates_memtable(self) -> None:
        with TemporaryDirectory() as wal_dir:
            with KVStoreEngine(Config(data_dir=wal_dir)) as store:
                store.batch_put([b"a", b"b"], [b"one", b"two"])

                self.assertEqual(store.read(b"a"), b"one")
                self.assertEqual(store.read(b"b"), b"two")

    def test_sstable_reads_are_repeatable(self) -> None:
        with TemporaryDirectory() as wal_dir:
            memtable = KVStoreEngine(Config(data_dir=wal_dir)).memtable
            memtable.put(Record(b"a", b"one"))
            memtable.put(Record(b"b", b"two"))

            sstable = SSTable.from_memtable(memtable, Path(wal_dir) / "000000.sst")

            self.assertEqual(sstable.read(b"a"), b"one")
            self.assertEqual(sstable.read(b"b"), b"two")
            self.assertEqual(
                dict(sstable.range(b"a", b"c")), {b"a": b"one", b"b": b"two"}
            )

    def test_replay_truncates_broken_header(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal = WAL(wal_dir)
            try:
                wal.append(Record(b"valid", b"value"))
            finally:
                wal._current.close()

            wal_path = Path(wal_dir) / "000000.log"
            valid_size = wal_path.stat().st_size
            with wal_path.open("ab") as file:
                file.write(b"\x01\x02")

            with KVStoreEngine(Config(data_dir=wal_dir)) as store:
                self.assertEqual(store.read(b"valid"), b"value")
                self.assertIsNone(store.read(b"broken"))
            self.assertEqual(wal_path.stat().st_size, valid_size)

    def test_replay_truncates_crc_mismatch(self) -> None:
        with TemporaryDirectory() as wal_dir:
            wal = WAL(wal_dir)
            try:
                wal.append(Record(b"valid", b"value"))
                wal.append(Record(b"broken", b"record"))
            finally:
                wal._current.close()

            wal_path = Path(wal_dir) / "000000.log"
            valid_size = 12 + len(b"valid") + len(b"value")
            with wal_path.open("r+b") as file:
                file.seek(valid_size)
                file.write(b"\x00\x00\x00\x00")

            with KVStoreEngine(Config(data_dir=wal_dir)) as store:
                self.assertEqual(store.read(b"valid"), b"value")
                self.assertIsNone(store.read(b"broken"))
            self.assertEqual(wal_path.stat().st_size, valid_size)
