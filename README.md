[![Server application](https://img.shields.io/github/workflow/status/doronz88/rpc-project/Server%20application?label=python%20package&style=plastic)](https://github.com/doronz88/rpc-project/actions/workflows/server-app.yml "Server application action")
[![Python application](https://img.shields.io/github/workflow/status/doronz88/rpc-project/Python%20application?label=server%20build&style=plastic)](https://github.com/doronz88/rpc-project/actions/workflows/python-app.yml "Python application action")

# rpc-project

## Description

This project includes two components:
* Server binary written in C exposing a protocol to call native C functions for controlling every aspect of 
* Client written in Python3 to communicate with the server

Simple remote control process requiring a single executable to be uploaded and run on the remote host.
This executable then provides a protocol to call native C functions which makes it possible to control
every aspect of the connected machine.

For more information about the client which utilizes these abilities, please view its README here:
https://github.com/doronz88/rpc-project/tree/master/src/rpcclient

## Building C Server

macOS & Linux:
```shell
git clone git@github.com:doronz88/rpc-project.git
cd src/remote_server
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
python3 -m rpcclient <HOST> ishell
```
