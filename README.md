# zShell

## Description

Inspired by [inSecure-SHell](https://github.com/fffaraz/inSecure-SHell), this shell's goal is to be the tinyest and simplest remote shell.

## Building

```shell
git clone git@github.com:doronz88/zshell.git
cd zshell/c
make all
```

## Running

To execute the server:

```shell
./c/server [-p port] [-s shell]
```

Connecting via:

```shell
./c/client HOST
```
