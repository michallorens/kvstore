# kvstore

Pluggable key-value storage

## Usage

Bring up the server:

```
uv sync --dev
uv run python -m kvstore.main
```

Import the client and use the API:

```
python
>> from kvstore.client import KVClient
>> client = Client()
>> client.put(b"key", b"value")
>> client.read(b"key")
b"value"
```
