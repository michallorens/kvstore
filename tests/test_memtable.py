from unittest import TestCase

from kvstore.memtable import MemTable


class TestMemTable(TestCase):
    def test_memtable_delete_replaces_value_with_tombstone(self) -> None:
        table = MemTable()
        table.put(b"key", b"value")

        table.delete(b"key")

        self.assertIsNone(table.read(b"key"))
        self.assertEqual(table.range(b"a", b"z"), {})
