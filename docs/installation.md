# Installation

## Client

Install the latest client from PyPI (requires **Python 3.10+**):

```shell
python3 -m pip install -U rpcclient
```

This provides two console entry points:

- `rpcclient [HOSTNAME]` — connect to a remote `rpcserver`
- `rpclocal` — control the **local** machine, no remote server required

## Server

Download and run the latest server artifact for your platform/arch from the latest
[server-publish GitHub Action](https://github.com/doronz88/rpc-project/actions/workflows/server-publish.yml),
or build it yourself (below).

## Building the server

!!! note
    Cross-platform builds are not currently supported — build on the target OS.

=== "macOS / iOS"

    Requires Xcode.

    ```bash
    brew install protobuf protobuf-c
    python3 -m pip install mypy-protobuf protobuf grpcio-tools
    git clone git@github.com:doronz88/rpc-project.git
    cd rpc-project
    make -C src/protos/ all
    cd src/rpcserver
    mkdir build && cd build
    cmake .. -DTARGET=OSX && make     # macOS
    cmake .. -DTARGET=IOS && make     # iOS
    ```

=== "Linux"

    ```bash
    sudo apt-get install -y protobuf-compiler libprotobuf-dev libprotoc-dev protobuf-c-compiler
    python3 -m pip install mypy-protobuf protobuf grpcio-tools
    git clone git@github.com:doronz88/rpc-project.git --recurse-submodules
    cd rpc-project
    make -C src/protos/ all
    cd src/rpcserver
    mkdir build && cd build
    cmake .. -DTARGET=LINUX && make
    ```
