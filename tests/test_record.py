from io import BytesIO
from unittest import TestCase

from kvstore.record import Record, TOMBSTONE_VALUE_SIZE


class TestRecord(TestCase):
    def test_parse_header(self) -> None:
        header = b"crc_\x00\x00\x00\x01\x00\x00\x00\x02"

        key_size, value_size, crc = Record._parse_header(header)

        self.assertEqual(key_size, 1)
        self.assertEqual(value_size, 2)
        self.assertEqual(crc, b"crc_")

    def test_validate(self) -> None:
        Record._validate(b'e"\xdfi\x00\x00\x00\x00\x00\x00\x00\x00', b"", b"")
        Record._validate(b"\xbb\x99\xff\x8a\x00\x00\x00\x00\xff\xff\xff\xff", b"", b"")
        Record._validate(b"\xb8\x91N[\x00\x00\x00\x03\x00\x00\x00\x05", b"key", b"value")

        with self.assertRaises(ValueError):
            Record._validate(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", b"", b"")

        with self.assertRaises(ValueError):
            Record._validate(
                b"\xb8\x91N[\x00\x00\x00\x03\x00\x00\x00\x04", b"key", b"value"
            )

        with self.assertRaises(ValueError):
            Record._validate(
                b"\xb8\x91N[\x00\x00\x00\x02\x00\x00\x00\x05", b"key", b"value"
            )

        with self.assertRaises(ValueError):
            Record._validate(
                b"\xb8\x91N[\x00\x00\x00\x03\x00\x00\x00\x05", b"key", b"val"
            )

        with self.assertRaises(ValueError):
            Record._validate(
                b"\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x05", b"key", b"value"
            )

    def test_get_value(self) -> None:
        self.assertEqual(Record.tombstone(b"key")._get_value(), b"")
        self.assertEqual(Record(b"key", b"value")._get_value(), b"value")

    def test_get_value_size(self) -> None:
        self.assertEqual(
            Record.tombstone(b"key")._get_value_size(), TOMBSTONE_VALUE_SIZE
        )
        self.assertEqual(Record(b"key", b"value")._get_value_size(), 5)

    def test_len(self) -> None:
        self.assertEqual(len(Record.tombstone(b"key")), 15)
        self.assertEqual(len(Record(b"key", b"value")), 20)

    def test_get_bytes(self) -> None:
        self.assertEqual(
            Record.tombstone(b"key")._get_bytes(), b"\x00\x00\x00\x03\xff\xff\xff\xffkey"
        )
        self.assertEqual(
            Record(b"key", b"value")._get_bytes(),
            b"\x00\x00\x00\x03\x00\x00\x00\x05keyvalue",
        )

    def test_checksum(self) -> None:
        self.assertEqual(Record.tombstone(b"key")._get_checksum(), b"\xf2J\xe45")
        self.assertEqual(Record(b"key", b"value")._get_checksum(), b"\xb8\x91N[")

    def test_to_bytes(self) -> None:
        self.assertEqual(
            Record.tombstone(b"key").to_bytes(),
            b"\xf2J\xe45\x00\x00\x00\x03\xff\xff\xff\xffkey",
        )
        self.assertEqual(
            Record(b"key", b"value").to_bytes(),
            b"\xb8\x91N[\x00\x00\x00\x03\x00\x00\x00\x05keyvalue",
        )

    def test_from_buffer(self) -> None:
        with BytesIO() as buffer:
            buffer.write(b"\xf2J\xe45\x00\x00\x00\x03\xff\xff\xff\xffkey")
            buffer.seek(0)

            self.assertEqual(Record.from_buffer(buffer), Record.tombstone(b"key"))

            buffer.seek(0)
            buffer.write(b"\xb8\x91N[\x00\x00\x00\x03\x00\x00\x00\x05keyvalue")
            buffer.seek(0)

            self.assertEqual(Record.from_buffer(buffer), Record(b"key", b"value"))
