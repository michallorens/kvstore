import random
import sys
import time
import resource

from tempfile import TemporaryDirectory
from unittest import TestCase

from kvstore import KVStoreAPI
from kvstore.config import Config
from kvstore.wal import WAL
from kvstore.memtable import MemTable


MAX_OPS = 100_000

resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))


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
    range_read_latencies: dict[int, list[int]],
    batch_put_latencies: list[int],
    delete_latencies: list[int],
    write_latencies: list[int],
    operations: int,
    elapsed_ns: int,
) -> None:
    throughput = operations / (elapsed_ns / 1_000_000_000)
    range_lines = "\n".join(
        f"\rREAD_RANGE_{size}: {format_latency_stats(range_read_latencies.get(size, []))}"
        for size in (10, 100, 1_000, 10_000)
    )

    sys.stdout.write(
        "\033[6A"
        f"\rREAD : {format_latency_stats(read_latencies)}\n"
        f"\rWRITE: {format_latency_stats(write_latencies)}\n"
        f"{range_lines}\n"
        f"\rWRITE_BATCH: {format_latency_stats(batch_put_latencies)}\n"
        f"\rDELETE: {format_latency_stats(delete_latencies)}\n"
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
            range_read_latencies: dict[int, list[int]] = {
                10: [],
                100: [],
                1_000: [],
                10_000: [],
            }
            batch_put_latencies: list[int] = []
            delete_latencies: list[int] = []
            write_latencies: list[int] = []

            operations = MAX_OPS

            print("READ")
            print("READ_RANGE_10")
            print("READ_RANGE_100")
            print("READ_RANGE_1000")
            print("READ_RANGE_10000")
            print("BATCH_PUT")
            print("DELETE")
            print("WRITE")
            print("RATE : starting...")

            start = time.perf_counter_ns()

            for i in range(operations):
                operation_type = rng.random()
                if not keys or operation_type < 0.55:
                    key = rng.randbytes(16)
                    value = rng.randbytes(128)

                    operation_start = time.perf_counter_ns()
                    kvstore.put(key, value)
                    elapsed = time.perf_counter_ns() - operation_start

                    write_latencies.append(elapsed)

                    keys.append(key)
                    values[key] = value

                elif operation_type < 0.65:
                    batch = [
                        (rng.randbytes(16), rng.randbytes(128))
                        for _ in range(rng.randint(2, 8))
                    ]
                    batch_keys, batch_values = zip(*batch)

                    operation_start = time.perf_counter_ns()
                    kvstore.batch_put(list(batch_keys), list(batch_values))
                    elapsed = time.perf_counter_ns() - operation_start

                    batch_put_latencies.append(elapsed)
                    keys.extend(batch_keys)
                    values.update(batch)

                elif operation_type < 0.70:
                    key = rng.choice(keys)

                    operation_start = time.perf_counter_ns()
                    kvstore.delete(key)
                    elapsed = time.perf_counter_ns() - operation_start

                    delete_latencies.append(elapsed)
                    keys.remove(key)
                    del values[key]

                elif operation_type < 0.95:
                    key = rng.choice(keys)

                    operation_start = time.perf_counter_ns()
                    result = kvstore.read(key)
                    elapsed = time.perf_counter_ns() - operation_start

                    read_latencies.append(elapsed)

                    self.assertEqual(result, values[key])

                else:
                    target_size = rng.choice((10, 100, 1_000, 10_000))
                    sorted_keys = sorted(values)
                    if len(sorted_keys) < 2:
                        continue

                    max_size = min(target_size, len(sorted_keys))
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

                    range_read_latencies[target_size].append(elapsed)

                    expected = {
                        key: value
                        for key, value in values.items()
                        if range_start <= key < range_end
                    }
                    self.assertEqual(result, expected)

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

            kvstore.wal.current.flush()
            kvstore.wal.current.close()

            replay_wal = WAL(wal_dir=wal_dir)
            replay_memtable = MemTable()
            replay_start = time.perf_counter_ns()
            replay_wal.replay(on_put=replay_memtable.put)
            replay_elapsed = time.perf_counter_ns() - replay_start

            print(f"REPLAY: {replay_elapsed / 1_000_000:.2f} ms")
            replay_wal.current.close()
            # replay_memtable.close()
