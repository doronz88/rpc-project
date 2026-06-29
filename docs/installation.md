# Installation

## Client

Install the latest client from PyPI:

```shell
python3 -m pip install -U rpcclient
```

Requires **Python 3.10+**.

## Server

Download and run the latest server artifact for your platform/arch:

- [rpcserver_iphoneos_arm64.zip](https://nightly.link/doronz88/rpc-project/workflows/server-publish/master/rpcserver_iphoneos_arm64.zip)
- [rpcserver_macosx_x86_64.zip](https://nightly.link/doronz88/rpc-project/workflows/server-publish/master/rpcserver_macosx_x86_64.zip)
- [rpcserver_ubuntu_x86_64.zip](https://nightly.link/doronz88/rpc-project/workflows/server-publish/master/rpcserver_ubuntu_x86_64.zip)

If your platform/arch isn't listed, build it yourself (below).

## Building the server

=== "macOS & Linux"

    ```shell
    git clone git@github.com:doronz88/rpc-project.git
    cd rpc-project/src/rpcserver
    make
    ```

=== "iOS"

    Requires Xcode.

    ```shell
    git clone git@github.com:doronz88/rpc-project.git
    cd rpc-project/src/rpcserver
    ./build_darwin.sh
    ```
