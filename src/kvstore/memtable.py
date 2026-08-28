from dataclasses import dataclass
import random


_TOMBSTONE = object()


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
        self._random = random.Random(seed)

    def put(self, key: bytes, value: bytes) -> None:
        self.root = self._insert(self.root, key, value)

    def delete(self, key: bytes) -> None:
        self.root = self._insert(self.root, key, _TOMBSTONE)

    def read(self, key: bytes) -> bytes | None:
        node = self.root
        while node is not None:
            if key == node.key:
                if node.value is _TOMBSTONE:
                    return None
                return node.value  # ty: ignore
            node = node.left if key < node.key else node.right
        return None

    def range(self, start: bytes, end: bytes) -> dict[bytes, bytes]:
        result: dict[bytes, bytes] = {}
        self._collect(self.root, start, end, result)
        return result

    def _insert(self, node: _Node | None, key: bytes, value: bytes | object) -> _Node:
        if node is None:
            return _Node(key, value, self._random.random())

        if key == node.key:
            node.value = value
            return node
        if key < node.key:
            node.left = self._insert(node.left, key, value)
            if node.left.priority < node.priority:
                return self._rotate_right(node)
        else:
            node.right = self._insert(node.right, key, value)
            if node.right.priority < node.priority:
                return self._rotate_left(node)
        return node

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
        if start <= node.key < end and node.value is not _TOMBSTONE:
            result[node.key] = node.value  # ty: ignore
        if node.key < end:
            self._collect(node.right, start, end, result)
