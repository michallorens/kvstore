from unittest import TestCase

from kvstore.memtable import MemTable
from kvstore.record import Record


class TestMemTable(TestCase):
    def test_memtable_delete_replaces_value_with_tombstone(self) -> None:
        table = MemTable()
        table.put(Record(b"key", b"value"))

        table.put(Record.tombstone(b"key"))

        self.assertIsNone(table.read(b"key"))
        self.assertEqual(table.range(b"a", b"z"), {b"key": None})
