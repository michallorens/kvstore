from kvstore.api import KVStoreAPI
from kvstore.server import KVServer


def main() -> None:
    with KVStoreAPI() as store:
        server = KVServer(store)
        server.run()


if __name__ == "__main__":
    main()
