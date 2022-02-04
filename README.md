[![Server application](https://img.shields.io/github/workflow/status/doronz88/zshell/Server%20application?label=python%20package&style=plastic)](https://github.com/doronz88/zshell/actions/workflows/server-app.yml "Server application action")
[![Python application](https://img.shields.io/github/workflow/status/doronz88/zshell/Python%20application?label=server%20build&style=plastic)](https://github.com/doronz88/zshell/actions/workflows/python-app.yml "Python application action")

# zShell

## Description

Simple remote control process requiring a single executable to be uploaded and run on the remote host.
This executable then provides a protocol to call native C functions which makes it possible to control
every aspect of the connected machine.

For more information about the client which utilizes these abilities, please view its README here:
https://github.com/doronz88/zshell/tree/master/src/pyzshell

## Building C Server

macOS & Linux:
```shell
git clone git@github.com:doronz88/zshell.git
cd src/remote_server
make
```

On iOS:
```shell
git clone git@github.com:doronz88/zshell.git
cd src
./build_ios.sh
```

## Installing python client

```shell
git clone git@github.com:doronz88/zshell.git
cd src/pyzshell
python3 -m pip install --user -U .
```

## Running

To execute the server:

```shell
./server [-p port]
```

Connecting via:

```shell
python3 -m pyzshell <HOST> ishell
```
