from unittest import TestCase

from kvstore.memtable import MemTable, NOT_FOUND
from kvstore.record import Record


class TestMemTable(TestCase):
    def test_put_and_read_returns_latest_value(self) -> None:
        table = MemTable()
        table.put(Record(b"b", b"two"))
        table.put(Record(b"a", b"one"))
        table.put(Record(b"a", b"updated"))

        self.assertEqual(table.read(b"a"), b"updated")
        self.assertEqual(table.read(b"b"), b"two")

    def test_read_missing_key_returns_not_found(self) -> None:
        table = MemTable()
        table.put(Record(b"a", b"one"))

        self.assertIs(table.read(b"missing"), NOT_FOUND)

    def test_range_only_includes_keys_within_window(self) -> None:
        table = MemTable()
        table.put(Record(b"a", b"one"))
        table.put(Record(b"b", b"two"))
        table.put(Record(b"d", b"four"))
        table.put(Record(b"e", b"five"))
        table.put(Record(b"f", b"six"))

        self.assertEqual(
            table.range(b"a", b"e"), {b"a": b"one", b"b": b"two", b"d": b"four"}
        )

    def test_memtable_delete_replaces_value_with_tombstone(self) -> None:
        table = MemTable()
        table.put(Record(b"key", b"value"))

        table.put(Record.tombstone(b"key"))

        self.assertIsNone(table.read(b"key"))
        self.assertEqual(table.range(b"a", b"z"), {b"key": None})

    def test_freeze_prevents_additional_writes(self) -> None:
        table = MemTable()
        table.put(Record(b"a", b"one"))
        table.freeze()

        with self.assertRaises(RuntimeError):
            table.put(Record(b"b", b"two"))
