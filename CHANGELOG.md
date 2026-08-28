# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-27

### Added

Initial naive implementation using WAL and reverse scan

```
READ : p50= 8319.01 us | p95=30979.33 us | p99=38531.56 us | p99.9=44637.43 us | max=57506.12 us
WRITE: p50=    3.14 us | p95=   10.09 us | p99=   14.39 us | p99.9=   33.10 us | max=  447.99 us
RATE : 298.59 ops/s
```

- Write-Ahead Logging
  - O(1) writes
  - O(N) reverse-scan reads
  - Log files rotate after reaching a configured threshold
- Random read/write benchmark
