# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Recovery time benchmark

## [0.5.0] - 2026-08-18

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
  - **NOTE** The range scans are impacting point reads, likely due to OS page cache eviction

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
