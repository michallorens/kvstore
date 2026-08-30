# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.12.0] - 2026-08-30

```
READ : p50=  126.19 us | p95=  682.71 us | p99=  919.27 us | p99.9= 1362.58 us | max= 3497.73 us
WRITE: p50=   17.29 us | p95=   34.25 us | p99=  101.01 us | p99.9=  721.69 us | max= 6367.66 us
READ_RANGE_1000: p50= 2881.12 us | p95= 4003.62 us | p99= 4445.27 us | p99.9= 6348.25 us | max= 9444.37 us
WRITE_BATCH: p50=   61.28 us | p95=  110.03 us | p99=  216.99 us | p99.9= 1161.29 us | max= 6816.68 us
DELETE: p50=   17.21 us | p95=   32.93 us | p99=   72.81 us | p99.9=  592.77 us | max= 6530.87 us
RATE : 1,873.20 ops/s
REPLAY: 230.55 ms
```

### Changed

- Moved MemTable flush to a background thread improving the tail-end write latency

## [0.11.2] - 2026-08-30

### Changed

- Moved opening files from constructor methods to context managers

## [0.11.1] - 2026-08-30

### Fixed

- MemTable drift due to WAL rotation during `BATCH_PUT`

### Removed

- KeyDir implementation - no longer used

## [0.11.0] - 2026-08-30

```
ncalls    tottime  percall  cumtime  percall  filename:lineno(function)
5064      0.637    0.000    7.797    0.002    /var/home/interviews/kvstore/src/kvstore/engine.py:93(read_key_range)
5066      0.006    0.000    7.071    0.001    /var/home/interviews/kvstore/src/kvstore/memtable.py:40(range)
5066      7.066    0.000    7.066    0.001    /var/home/interviews/kvstore/src/kvstore/memtable.py:78(_collect)
219069    0.127    0.000    4.763    0.000    /var/home/interviews/kvstore/src/kvstore/memtable.py:24(put)
219068    4.333    0.000    4.635    0.000    /var/home/interviews/kvstore/src/kvstore/memtable.py:45(_insert)
```

100k records:

```
READ : p50=  155.70 us | p95=  811.12 us | p99= 1250.92 us | p99.9= 2496.47 us | max= 5248.83 us
WRITE: p50=   18.76 us | p95=   46.11 us | p99=   65.47 us | p99.9=  108.23 us | max=95330.46 us
READ_RANGE_1000: p50= 3195.47 us | p95= 5687.34 us | p99= 8822.37 us | p99.9=15272.65 us | max=21034.93 us
WRITE_BATCH: p50=   70.38 us | p95=  157.09 us | p99=  251.29 us | p99.9=  576.06 us | max=88197.46 us
DELETE: p50=   18.73 us | p95=   44.75 us | p99=   67.17 us | p99.9=   91.07 us | max=  139.60 us
RATE : 1,599.98 ops/s
REPLAY: 313.27 ms
```

1M records:

```
READ : p50= 1496.99 us | p95= 6381.99 us | p99=22765.54 us | p99.9=37972.42 us | max=78890.80 us
WRITE: p50=   23.50 us | p95=   56.90 us | p99=   73.86 us | p99.9=  108.36 us | max=259438.42 us=   55.12 us | p99=   69.02 us | p99.9=
READ_RANGE_1000: p50= 6920.32 us | p95=12707.36 us | p99=51272.36 us | p99.9=66970.52 us | max=152931.81 us
WRITE_BATCH: p50=   83.18 us | p95=  164.25 us | p99=  248.31 us | p99.9=  567.34 us | max=159264.49 us
DELETE: p50=   24.02 us | p95=   57.21 us | p99=   73.98 us | p99.9=  111.45 us | max=93521.72 us
RATE : 224.40 ops/s
REPLAY: 344.13 ms
```

- Improved time of replay/recovery
- Degraded tail-end due to SSTables being flushed synchronously
- Write latency remains constant regardless of volume, reads degrade due to growing number of SSTables to scan

### Added

- SOLUTION.md

### Fixed

- Current WAL file left open
- Writing SSTables and corresponding hint files atomically
- WAL replay skipping log files with corresponding SSTables
  - Recovery time is down from 1400us to 300us for 100k records
  - SSTables however come at the cost of read time which has risen to p50=155us
- SSTable list not populated on startup
- Heavy sorting in the benchmark polluting profiler results
- Not benchmarking reads against tombstoned records, due to removing keys from benchmark cache

### Changed

- Limited WAL size in benchmark to test WAL rotation, SSTables and replay
- Parametrized the benchmark (op ratios, range read size, max ops & memory limit)

## [0.10.0] - 2026-08-30

### Added

- Networking
- Missing test cases

### Fixed

- Bug when opening hint files for writing
- Type hints in various methods

## [0.9.0] - 2026-08-30

```
READ : p50=    5.71 us | p95=   25.78 us | p99=  148.05 us | p99.9=  262.70 us | max=  561.99 us568.26 us
WRITE: p50=   16.82 us | p95=   44.91 us | p99=   58.40 us | p99.9=   86.02 us | max= 1193.14 us1814.54 us
READ_RANGE_10: p50=   34.05 us | p95=   60.91 us | p99=  253.37 us | p99.9=  324.08 us | max=  487.18 us us
READ_RANGE_100: p50=  108.22 us | p95=  181.81 us | p99=  345.43 us | p99.9=  476.74 us | max=  568.26 us
READ_RANGE_1000: p50=  786.37 us | p95= 1049.35 us | p99= 1390.56 us | p99.9= 1672.96 us | max= 1814.54 us
READ_RANGE_10000: p50= 8167.65 us | p95=10636.90 us | p99=12700.51 us | p99.9=19134.07 us | max=20413.37 us
WRITE_BATCH: p50=   67.40 us | p95=  127.41 us | p99=  186.30 us | p99.9= 1835.39 us | max=10468.75 us
DELETE: p50=   16.01 us | p95=   41.42 us | p99=   53.23 us | p99.9=   76.26 us | max=  475.58 us
RATE : 731.56 ops/s
```

### Added

- Sparse indexes to speed up lookup in SSTables, indexes are persisted alongside SSTables as .hint files
  as to not impact the replay/recovery time

## [0.8.0] - 2026-08-30

```
READ : p50=    7.77 us | p95=   44.69 us | p99=  222.59 us | p99.9=  500.58 us | max= 2263.26 us593.26 us
WRITE: p50=   22.25 us | p95=   62.56 us | p99=  114.44 us | p99.9=  198.07 us | max= 8280.44 us5937.46 us
READ_RANGE_10: p50=   40.30 us | p95=  107.25 us | p99=  307.99 us | p99.9=  550.56 us | max=  889.14 us us
READ_RANGE_100: p50=  135.47 us | p95=  342.30 us | p99=  560.45 us | p99.9=  869.08 us | max= 1593.26 us
READ_RANGE_1000: p50= 1027.29 us | p95= 2252.69 us | p99= 3405.28 us | p99.9= 5048.30 us | max= 5937.46 us
READ_RANGE_10000: p50=10658.42 us | p95=23216.20 us | p99=33794.60 us | p99.9=42819.12 us | max=49853.54 us
WRITE_BATCH: p50=   92.40 us | p95=  236.94 us | p99=  428.85 us | p99.9= 2485.49 us | max= 8366.80 us
DELETE: p50=   20.83 us | p95=   55.11 us | p99=  105.18 us | p99.9=  181.03 us | max=  994.29 us
RATE : 461.60 ops/s
```

### Added

- SSTables to flush MemTables to disk, triggered whenever WAL log rotates for simplicity but also to
  be able to easily check WAL/SSTable integrity
- Flushing the SSTable is currently performed synchronously and can be seen impacting the write speed

### Changed

- Benchmark to profile range reads separately for reads of 10 to 10000 records
- Max WAL size to 64MB

## [0.7.0] - 2026-08-29

### Added

- Simulated limited memory, causing MemoryError early due to large in-memory caches

## [0.6.0] - 2026-08-29

```
READ : p50=    5.04 us | p95=  317.68 us | p99= 1716.83 us | p99.9= 2669.79 us | max= 4715.19 us
WRITE: p50=   18.62 us | p95=   46.56 us | p99=   63.82 us | p99.9=  222.93 us | max= 4280.50 us
READ_RANGE: p50= 7629.41 us | p95=44825.62 us | p99=64052.53 us | p99.9=77436.97 us | max=91935.88 us
WRITE_BATCH: p50=   76.77 us | p95=  141.70 us | p99=  208.56 us | p99.9=  559.01 us | max= 4579.96 us
DELETE: p50=   18.38 us | p95=   40.47 us | p99=   54.59 us | p99.9=   73.34 us | max=  172.09 us
RATE : 834.49 ops/s
REPLAY: 1326.34 ms (100,162 keys)
```

### Added

- MemTable implemented as a treap structure

## [0.5.2] - 2026-08-28

```
READ : p50=   22.12 us | p95= 1437.90 us | p99= 3896.12 us | p99.9= 5817.02 us | max=13858.40 us
WRITE: p50=    8.01 us | p95=   35.96 us | p99=   47.66 us | p99.9=   68.98 us | max= 1045.03 us
READ_RANGE: p50=58202.17 us | p95=130206.43 us | p99=154445.15 us | p99.9=208530.98 us | max=250112.51 us
WRITE_BATCH: p50=   24.86 us | p95=   58.96 us | p99=   80.11 us | p99.9=  223.43 us | max= 4649.33 us
DELETE: p50=   10.28 us | p95=   31.61 us | p99=   42.41 us | p99.9=   54.82 us | max=  186.41 us
RATE : 245.03 ops/s
REPLAY: 1269.80 ms (100,162 keys)
```

### Added

- Recovery time benchmark

## [0.5.1] - 2026-08-28

### Changed

- Moved WAL replay logic from KeyDir to WAL class, it now uses callbacks to register consumers of records

## [0.5.0] - 2026-08-28

```
READ : p50=   23.05 us | p95= 1385.03 us | p99= 3656.64 us | p99.9= 5948.48 us | max=10140.88 us
WRITE: p50=    8.06 us | p95=   35.60 us | p99=   50.13 us | p99.9=   76.18 us | max= 1115.10 us
READ_RANGE: p50=61584.01 us | p95=156128.86 us | p99=198229.70 us | p99.9=316520.53 us | max=479077.60 us
WRITE_BATCH: p50=   25.01 us | p95=   58.45 us | p99=   84.11 us | p99.9=  217.25 us | max= 4578.37 us
DELETE: p50=   10.03 us | p95=   32.28 us | p99=   43.85 us | p99.9=   63.93 us | max=  106.25 us
RATE : 242.69 ops/s
```

### Added

- Batched writes
- Deleting records using tombstones
- Fsync after flush to prevent data loss on crash
  - **NOTE** Observed no significant impact on write performance

### Changed

- Cleaned up WAL implementation

### Fixed

- Writing a record using a single write call

## [0.4.0] - 2026-08-28

```
READ : p50=   15.67 us | p95=  631.07 us | p99= 1858.75 us | p99.9= 3344.89 us | max= 5909.88 us
WRITE: p50=    6.47 us | p95=   24.72 us | p99=   37.65 us | p99.9=   53.97 us | max= 2080.92 us
READ_RANGE: p50=31794.89 us | p95=61994.50 us | p99=73037.52 us | p99.9=94226.85 us | max=109517.12 us
RATE : 498.60 ops/s
```

### Added

- Naive key range scan of WAL files
  - **NOTE** The range scans are impacting point reads, likely due to OS page cache eviction, profiler evidence:
    > ncalls tottime percall cumtime percall filename:lineno(function)
    >
    > 2489 0.010 0.000 0.081 0.000 /var/home/interviews/kvstore/src/kvstore/keydir.py:45(get)

## [0.3.0] - 2026-08-28

```
READ : p50=   13.41 us | p95=   26.48 us | p99=   36.05 us | p99.9=  126.75 us | max= 2962.91 us
WRITE: p50=    5.94 us | p95=   11.71 us | p99=   16.88 us | p99.9=   30.84 us | max= 2012.38 us
RATE : 20,753.20 ops/s
```

### Added

- Torn-write recovery using a CRC checksum

## [0.2.2] - 2026-08-28

```
READ : p50=   18.27 us | p95=   36.87 us | p99=   49.06 us | p99.9=  135.82 us | max= 3024.31 us
WRITE: p50=    5.41 us | p95=   10.88 us | p99=   15.67 us | p99.9=   30.92 us | max= 2302.20 us
RATE : 19,768.13 ops/s
```

### Fixed

- Calling `Path.stem` every `append` caused performance degradation

## [0.2.1] - 2026-08-28

```
READ : p50=   17.95 us | p95=   32.33 us | p99=   43.86 us | p99.9=  103.87 us | max= 1567.02 us
WRITE: p50=   58.99 us | p95=  111.16 us | p99=  167.85 us | p99.9=  224.68 us | max= 3159.34 us
RATE : 12,192.51 ops/s
```

### Changed

- Keeping file descriptors open for random access reads
  - **IMPORTANT** This requires limiting the number of open file descriptors later

## [0.2.0] - 2026-08-28

```
READ : p50=   57.70 us | p95=   86.88 us | p99=  111.27 us | p99.9=  153.19 us | max=  688.88 us
WRITE: p50=  129.87 us | p95=  192.42 us | p99=  284.78 us | p99.9=  410.27 us | max= 3880.83 us
RATE : 5,913.99 ops/s
```

### Added

- KeyDir index of segments/offsets holding current value for particular key

## [0.1.0] - 2026-08-27

```
READ : p50= 8319.01 us | p95=30979.33 us | p99=38531.56 us | p99.9=44637.43 us | max=57506.12 us
WRITE: p50=    3.14 us | p95=   10.09 us | p99=   14.39 us | p99.9=   33.10 us | max=  447.99 us
RATE : 298.59 ops/s
```

### Added

Initial naive implementation using WAL and reverse scan

- Write-Ahead Logging
  - O(1) writes
  - O(N) reverse-scan reads
  - Log files rotate after reaching a configured threshold
- Random read/write benchmark
