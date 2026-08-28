import os


class Config:
    DEFAULT_WAL_DIR = "wal"
    DEFAULT_MAX_WAL_SIZE = 1024 * 1024
    wal_dir: str
    max_wal_size: int

    def __init__(
        self,
        wal_dir: str | None = None,
        max_wal_size: int | None = None,
    ) -> None:
        configured_wal_dir = os.getenv("KVSTORE_WAL_DIR")
        configured_max_wal_size = os.getenv("KVSTORE_MAX_WAL_SIZE")

        self.wal_dir = (
            wal_dir
            if wal_dir is not None
            else configured_wal_dir or self.DEFAULT_WAL_DIR
        )
        self.max_wal_size = (
            max_wal_size
            if max_wal_size is not None
            else int(configured_max_wal_size)
            if configured_max_wal_size is not None
            else self.DEFAULT_MAX_WAL_SIZE
        )
