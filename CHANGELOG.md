# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
