import os


class Config:
    DEFAULT_DATA_DIR = "wal"
    DEFAULT_MAX_WAL_SIZE = 64 * 1024 * 1024

    def __init__(
        self,
        data_dir: str | None = None,
        max_wal_size: int | None = None,
    ) -> None:
        configured_data_dir = os.getenv("KVSTORE_DATA_DIR")
        configured_max_wal_size = os.getenv("KVSTORE_MAX_WAL_SIZE")

        self.data_dir = (
            data_dir
            if data_dir is not None
            else configured_data_dir or self.DEFAULT_DATA_DIR
        )
        self.max_wal_size = (
            max_wal_size
            if max_wal_size is not None
            else int(configured_max_wal_size)
            if configured_max_wal_size is not None
            else self.DEFAULT_MAX_WAL_SIZE
        )
