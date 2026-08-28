import random
import sys
import time

from tempfile import TemporaryDirectory
from unittest import TestCase

from kvstore import KVStoreAPI
from kvstore.config import Config


MAX_OPS = 10_000


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
    write_latencies: list[int],
    operations: int,
    elapsed_ns: int,
) -> None:
    throughput = operations / (elapsed_ns / 1_000_000_000)

    sys.stdout.write(
        "\033[3A"
        f"\rREAD : {format_latency_stats(read_latencies)}\n"
        f"\rWRITE: {format_latency_stats(write_latencies)}\n"
        f"\rRATE : {throughput:,.2f} ops/s                \n"
    )
    sys.stdout.flush()


class TestKVStoreBenchmark(TestCase):
    def test_random_reads_and_writes(self):
        with (
            TemporaryDirectory() as wal_dir,
            KVStoreAPI(
                config=Config(wal_dir=wal_dir),
            ) as kvstore,
        ):
            rng = random.Random(42)

            keys: list[bytes] = []
            values: dict[bytes, bytes] = {}

            read_latencies: list[int] = []
            write_latencies: list[int] = []

            operations = MAX_OPS

            print("READ")
            print("WRITE")
            print("RATE : starting...")

            start = time.perf_counter_ns()

            for i in range(operations):
                if not keys or rng.random() < 0.7:
                    key = rng.randbytes(16)
                    value = rng.randbytes(128)

                    operation_start = time.perf_counter_ns()
                    kvstore.put(key, value)
                    elapsed = time.perf_counter_ns() - operation_start

                    write_latencies.append(elapsed)

                    keys.append(key)
                    values[key] = value

                else:
                    key = rng.choice(keys)

                    operation_start = time.perf_counter_ns()
                    result = kvstore.read(key)
                    elapsed = time.perf_counter_ns() - operation_start

                    read_latencies.append(elapsed)

                    self.assertEqual(result, values[key])

                if (i + 1) % 1_000 == 0:
                    elapsed = time.perf_counter_ns() - start
                    print_stats(
                        read_latencies,
                        write_latencies,
                        i + 1,
                        elapsed,
                    )

            elapsed = time.perf_counter_ns() - start

            print()
            print(
                f"Final throughput: {operations / (elapsed / 1_000_000_000):,.2f} ops/s"
            )
