from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from kvstore.memtable import MemTable, NOT_FOUND
from kvstore.record import Record
from kvstore.sstable import SSTable


class TestSSTable(TestCase):
    def test_from_memtable_creates_serialized_table(self) -> None:
        with TemporaryDirectory() as wal_dir:
            memtable = MemTable()
            memtable.put(Record(b"a", b"one"))
            memtable.put(Record(b"b", b"two"))

            sstable = SSTable.from_memtable(memtable, Path(wal_dir) / "000000.sst")

            self.assertEqual(sstable.read(b"a"), b"one")
            self.assertEqual(sstable.read(b"b"), b"two")

    def test_read_missing_key_returns_not_found(self) -> None:
        with TemporaryDirectory() as wal_dir:
            memtable = MemTable()
            memtable.put(Record(b"a", b"one"))

            sstable = SSTable.from_memtable(memtable, Path(wal_dir) / "000000.sst")

            self.assertIs(sstable.read(b"missing"), NOT_FOUND)

    def test_range_returns_key_values_and_handles_tombstones(self) -> None:
        with TemporaryDirectory() as wal_dir:
            memtable = MemTable()
            memtable.put(Record(b"a", b"one"))
            memtable.put(Record(b"b", b"two"))
            memtable.put(Record.tombstone(b"c"))
            memtable.put(Record(b"d", b"four"))

            sstable = SSTable.from_memtable(memtable, Path(wal_dir) / "000000.sst")

            self.assertEqual(
                dict(sstable.range(b"a", b"e")),
                {b"a": b"one", b"b": b"two", b"c": None, b"d": b"four"},
            )

    def test_repeated_reads_to_ensure_correct_seeking(self) -> None:
        with TemporaryDirectory() as wal_dir:
            memtable = MemTable()
            memtable.put(Record(b"a", b"one"))
            memtable.put(Record(b"b", b"two"))

            sstable = SSTable.from_memtable(memtable, Path(wal_dir) / "000000.sst")

            self.assertEqual(sstable.read(b"a"), b"one")
            self.assertEqual(sstable.read(b"a"), b"one")
            self.assertEqual(
                dict(sstable.range(b"a", b"c")), {b"a": b"one", b"b": b"two"}
            )
            self.assertEqual(
                dict(sstable.range(b"a", b"c")), {b"a": b"one", b"b": b"two"}
            )
