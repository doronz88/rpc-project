# Rpc-Project

<!-- markdownlint-disable MD013 -->
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/doronz88/rpc-project)
<!-- markdownlint-enable MD013 -->

`rpc-project` is a simple, powerful **RPC service for controlling every aspect of a remote
machine**. A small C **server** exposes a protocol for calling native functions; a Python
**client** (`rpcclient`) turns that into a rich, scriptable API — a swiss-army knife for QA
automation, development, and software research.

## Install

```shell
python3 -m pip install -U rpcclient
```

- `rpcclient [HOSTNAME]` — connect to a remote `rpcserver`
- `rpclocal` — control the local machine, no remote server required

For the server binary (download or build), see the installation guide below.

## Documentation

📖 **Full documentation: <https://doronz88.github.io/rpc-project/>**

- [Installation & building the server](https://doronz88.github.io/rpc-project/installation/)
- [Quick start](https://doronz88.github.io/rpc-project/guides/quickstart/)
- [Calling native functions](https://doronz88.github.io/rpc-project/guides/calling-native-functions/)
- [API reference](https://doronz88.github.io/rpc-project/api/)

The docs are built from [`docs/`](docs/) with MkDocs (`mkdocs.yml`).

## License

Licensed under GPL-3.0 — see [LICENSE](LICENSE).
