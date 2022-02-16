[![Server application](https://img.shields.io/github/workflow/status/doronz88/rpc-project/Server%20application?label=python%20package&style=plastic)](https://github.com/doronz88/rpc-project/actions/workflows/server-app.yml "Server application action")
[![Python application](https://img.shields.io/github/workflow/status/doronz88/rpc-project/Python%20application?label=server%20build&style=plastic)](https://github.com/doronz88/rpc-project/actions/workflows/python-app.yml "Python application action")

# rpc-project

## Description

Simple RPC service providing an API for controlling every aspect of the target machine for automation purposes.

This project includes two components:

* Server binary written in C exposing a protocol to call native C functions.
* Client written in Python3 to communicate with the server

The python client utilizes the ability to call native functions in order to provide APIs for different aspects:

* Remote shell commands
* Filesystem management (APIs for `open()`, `read()`, etc...)
* Network management (WiFi scan, TCP connect, etc...)
* Darwin only:
  * Multimedia automation (recording and playing)
  * Preferences managemnent (remote manage CFPreference and SCPreferences)
  * Process management (kill, list, query open FDs, etc...)

## Building C Server

macOS & Linux:

```shell
git clone git@github.com:doronz88/rpc-project.git
cd src/rpcserver
make
```

On iOS:

```shell
git clone git@github.com:doronz88/rpc-project.git
cd src
./build_ios.sh
```

## Installing python client

```shell
git clone git@github.com:doronz88/rpc-project.git
cd src/rpcclient
python3 -m pip install --user -U .
```

## Running

To execute the server:

```shell
./server [-p port]
```

Connecting via:

```shell
python3 -m rpcclient <HOST> [-p port]
```
