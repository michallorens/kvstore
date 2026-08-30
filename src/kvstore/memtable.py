from dataclasses import dataclass
import random

from kvstore.record import Record, TOMBSTONE

NOT_FOUND = object()


@dataclass
class _Node:
    key: bytes
    value: bytes | object
    priority: float
    left: "_Node | None" = None
    right: "_Node | None" = None


class MemTable:
    def __init__(self, seed: int | None = None) -> None:
        self.root: _Node | None = None
        self._frozen: bool = False
        self._random = random.Random(seed)
        self._size = 0

    def put(self, record: Record) -> None:
        if self._frozen:
            raise RuntimeError("memtable is frozen")

        self.root, inserted = self._insert(self.root, record)

        if inserted:
            self._size += 1

    def __len__(self) -> int:
        return self._size

    def read(self, key: bytes) -> bytes | object | None:
        node = self.root
        while node is not None:
            if key == node.key:
                if node.value is TOMBSTONE:
                    return None
                return node.value
            node = node.left if key < node.key else node.right
        return NOT_FOUND

    def range(self, start: bytes, end: bytes) -> dict[bytes, bytes]:
        result: dict[bytes, bytes] = {}
        self._collect(self.root, start, end, result)
        return result

    def _insert(self, node: _Node | None, record: Record) -> tuple[_Node, bool]:
        if node is None:
            return (_Node(record.key, record.value, self._random.random()), True)

        if record.key == node.key:
            node.value = record.value
            return node, False

        if record.key < node.key:
            node.left, inserted = self._insert(node.left, record)
            if node.left.priority < node.priority:
                node = self._rotate_right(node)

        else:
            node.right, inserted = self._insert(node.right, record)
            if node.right.priority < node.priority:
                node = self._rotate_left(node)

        return node, inserted

    @staticmethod
    def _rotate_right(node: _Node) -> _Node:
        child = node.left
        assert child is not None
        node.left = child.right
        child.right = node
        return child

    @staticmethod
    def _rotate_left(node: _Node) -> _Node:
        child = node.right
        assert child is not None
        node.right = child.left
        child.left = node
        return child

    def _collect(
        self,
        node: _Node | None,
        start: bytes,
        end: bytes,
        result: dict[bytes, bytes],
    ) -> None:
        if node is None:
            return
        if node.key >= start:
            self._collect(node.left, start, end, result)
        if start <= node.key < end:
            result[node.key] = (
                None if node.value is TOMBSTONE else node.value  # ty: ignore
            )
        if node.key < end:
            self._collect(node.right, start, end, result)

    def freeze(self) -> None:
        self._frozen = True

    def _in_order(self, node: _Node | None):
        if node is None:
            return

        yield from self._in_order(node.left)
        yield (
            Record.tombstone(node.key)
            if node.value is TOMBSTONE
            else Record(node.key, node.value)
        )
        yield from self._in_order(node.right)

    def records(self):
        yield from self._in_order(self.root)
