import os
import random
import sys
import time
import resource

from bisect import bisect_left, insort
from tempfile import TemporaryDirectory
from unittest import TestCase

from kvstore import KVStoreEngine
from kvstore.config import Config


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


MAX_OPS = int(os.getenv("KVSTORE_MAX_OPS", "100000"))
MAX_MEM = int(os.getenv("KVSTORE_MAX_MEM", "512"))
MAX_WAL = int(os.getenv("KVSTORE_MAX_WAL", "4"))

WRITE_RATIO = _env_float("KVSTORE_WRITE_RATIO", 0.55)
BATCH_PUT_RATIO = _env_float("KVSTORE_BATCH_PUT_RATIO", 0.10)
DELETE_RATIO = _env_float("KVSTORE_DELETE_RATIO", 0.05)
RANGE_READ_RATIO = _env_float("KVSTORE_RANGE_READ_RATIO", 0.05)
POINT_READ_RATIO = _env_float("KVSTORE_POINT_READ_RATIO", 0.25)
RANGE_QUERY_SIZE = int(os.getenv("KVSTORE_RANGE_QUERY_SIZE", "1000"))

assert (
    abs(
        (
            WRITE_RATIO
            + BATCH_PUT_RATIO
            + DELETE_RATIO
            + RANGE_READ_RATIO
            + POINT_READ_RATIO
        )
        - 1.0
    )
    < 1e-9
)

resource.setrlimit(resource.RLIMIT_AS, (MAX_MEM * 1024 * 1024, MAX_MEM * 1024 * 1024))


def percentile(values: list[int], p: float) -> float:
    values = sorted(values)
    index = int((len(values) - 1) * p / 100)
    return values[index]


def format_latency_stats(latencies: list[int]) -> str:
    if not latencies:
        return "no samples"

    return (
        f"p50={percentile(latencies, 50) / 1_000:8.2f} us | "
        f"p95={percentile(latencies, 95) / 1_000:8.2f} us | "
        f"p99={percentile(latencies, 99) / 1_000:8.2f} us | "
        f"p99.9={percentile(latencies, 99.9) / 1_000:8.2f} us | "
        f"max={max(latencies) / 1_000:8.2f} us"
    )


def print_stats(
    read_latencies: list[int],
    range_read_latencies: list[int],
    batch_put_latencies: list[int],
    delete_latencies: list[int],
    write_latencies: list[int],
    operations: int,
    elapsed_ns: int,
) -> None:
    throughput = operations / (elapsed_ns / 1_000_000_000)

    sys.stdout.write(
        "\033[6A"
        f"\rREAD : {format_latency_stats(read_latencies)}\n"
        f"\rWRITE: {format_latency_stats(write_latencies)}\n"
        f"\rREAD_RANGE_{RANGE_QUERY_SIZE}: {format_latency_stats(range_read_latencies)}\n"
        f"\rWRITE_BATCH: {format_latency_stats(batch_put_latencies)}\n"
        f"\rDELETE: {format_latency_stats(delete_latencies)}\n"
        f"\rRATE : {throughput:,.2f} ops/s                \n"
    )
    sys.stdout.flush()


class TestKVStoreBenchmark(TestCase):
    def _profile_write(
        self,
        kvstore: KVStoreEngine,
        rng: random.Random,
        keys: list[bytes],
        values: dict[bytes, bytes | None],
        sorted_keys: list[bytes],
        write_latencies: list[int],
    ) -> None:
        key = rng.randbytes(16)
        value = rng.randbytes(128)

        operation_start = time.perf_counter_ns()
        kvstore.put(key, value)
        elapsed = time.perf_counter_ns() - operation_start

        write_latencies.append(elapsed)
        if key not in values:
            keys.append(key)
        values[key] = value

        index = bisect_left(sorted_keys, key)
        if index == len(sorted_keys) or sorted_keys[index] != key:
            insort(sorted_keys, key)

    def _profile_batch_put(
        self,
        kvstore: KVStoreEngine,
        rng: random.Random,
        keys: list[bytes],
        values: dict[bytes, bytes | None],
        sorted_keys: list[bytes],
        batch_put_latencies: list[int],
    ) -> None:
        batch = [
            (rng.randbytes(16), rng.randbytes(128)) for _ in range(rng.randint(2, 8))
        ]
        batch_keys, batch_values = zip(*batch)

        operation_start = time.perf_counter_ns()
        kvstore.batch_put(list(batch_keys), list(batch_values))
        elapsed = time.perf_counter_ns() - operation_start

        batch_put_latencies.append(elapsed)
        for key, value in batch:
            if key not in values:
                keys.append(key)
            values[key] = value

            index = bisect_left(sorted_keys, key)
            if index == len(sorted_keys) or sorted_keys[index] != key:
                insort(sorted_keys, key)

    def _profile_delete(
        self,
        kvstore: KVStoreEngine,
        rng: random.Random,
        keys: list[bytes],
        values: dict[bytes, bytes | None],
        sorted_keys: list[bytes],
        delete_latencies: list[int],
    ) -> None:
        key = rng.choice(keys)

        operation_start = time.perf_counter_ns()
        kvstore.delete(key)
        elapsed = time.perf_counter_ns() - operation_start

        delete_latencies.append(elapsed)
        values[key] = None

        index = bisect_left(sorted_keys, key)
        if index == len(sorted_keys) or sorted_keys[index] != key:
            insort(sorted_keys, key)

    def _profile_read(
        self,
        kvstore: KVStoreEngine,
        rng: random.Random,
        keys: list[bytes],
        values: dict[bytes, bytes | None],
        read_latencies: list[int],
    ) -> None:
        if not keys or rng.random() < 0.20:
            key = rng.randbytes(16)
            while key in values:
                key = rng.randbytes(16)
        else:
            key = rng.choice(keys)

        operation_start = time.perf_counter_ns()
        result = kvstore.read(key)
        elapsed = time.perf_counter_ns() - operation_start

        read_latencies.append(elapsed)
        self.assertEqual(result, values.get(key))

    def _profile_range_read(
        self,
        kvstore: KVStoreEngine,
        rng: random.Random,
        values: dict[bytes, bytes | None],
        sorted_keys: list[bytes],
        range_read_latencies: list[int],
    ) -> bool:
        if len(sorted_keys) < 2:
            return False

        max_size = min(RANGE_QUERY_SIZE, len(sorted_keys))
        start_index = rng.randrange(0, len(sorted_keys) - max_size + 1)
        end_index = start_index + max_size
        range_start = sorted_keys[start_index]
        range_end = (
            sorted_keys[end_index]
            if end_index < len(sorted_keys)
            else b"\xff" * len(sorted_keys[-1])
        )

        operation_start = time.perf_counter_ns()
        result = kvstore.read_key_range(range_start, range_end)
        elapsed = time.perf_counter_ns() - operation_start

        range_read_latencies.append(elapsed)

        expected = {
            key: value
            for key, value in values.items()
            if value is not None and range_start <= key < range_end
        }
        self.assertEqual(result, expected)
        return True

    def test_random_reads_and_writes(self):
        with (
            TemporaryDirectory() as wal_dir,
            KVStoreEngine(
                config=Config(
                    data_dir=wal_dir,
                    max_wal_size=MAX_WAL * 1024 * 1024,
                ),
            ) as kvstore,
        ):
            print(wal_dir)
            rng = random.Random(42)

            keys: list[bytes] = []
            values: dict[bytes, bytes | None] = {}
            sorted_keys: list[bytes] = []

            read_latencies: list[int] = []
            range_read_latencies: list[int] = []
            batch_put_latencies: list[int] = []
            delete_latencies: list[int] = []
            write_latencies: list[int] = []

            operations = MAX_OPS

            print("READ")
            print("READ_RANGE")
            print("BATCH_PUT")
            print("DELETE")
            print("WRITE")
            print("RATE : starting...")

            start = time.perf_counter_ns()

            for i in range(operations):
                operation_type = rng.random()
                if not keys or operation_type < WRITE_RATIO:
                    self._profile_write(
                        kvstore,
                        rng,
                        keys,
                        values,
                        sorted_keys,
                        write_latencies,
                    )
                elif operation_type < WRITE_RATIO + BATCH_PUT_RATIO:
                    self._profile_batch_put(
                        kvstore,
                        rng,
                        keys,
                        values,
                        sorted_keys,
                        batch_put_latencies,
                    )
                elif operation_type < WRITE_RATIO + BATCH_PUT_RATIO + DELETE_RATIO:
                    if not keys:
                        continue
                    self._profile_delete(
                        kvstore,
                        rng,
                        keys,
                        values,
                        sorted_keys,
                        delete_latencies,
                    )
                elif (
                    operation_type
                    < WRITE_RATIO + BATCH_PUT_RATIO + DELETE_RATIO + POINT_READ_RATIO
                ):
                    if not keys:
                        continue
                    self._profile_read(
                        kvstore,
                        rng,
                        keys,
                        values,
                        read_latencies,
                    )
                else:
                    self._profile_range_read(
                        kvstore,
                        rng,
                        values,
                        sorted_keys,
                        range_read_latencies,
                    )

                if (i + 1) % 1_000 == 0:
                    elapsed = time.perf_counter_ns() - start
                    print_stats(
                        read_latencies,
                        range_read_latencies,
                        batch_put_latencies,
                        delete_latencies,
                        write_latencies,
                        i + 1,
                        elapsed,
                    )

            elapsed = time.perf_counter_ns() - start

            print()
            print(
                f"Final throughput: {operations / (elapsed / 1_000_000_000):,.2f} ops/s"
            )

            kvstore.wal.close()

            replay_start = time.perf_counter_ns()
            with KVStoreEngine(config=Config(data_dir=wal_dir)) as replay_engine:
                replay_elapsed = time.perf_counter_ns() - replay_start
                print(f"REPLAY: {replay_elapsed / 1_000_000:.2f} ms")

                for key, expected in values.items():
                    self.assertEqual(replay_engine.read(key), expected)
