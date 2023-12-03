#!/bin/bash
protoc rpc.proto --python_out=../rpcclient/rpcclient/protos/ --mypy_out=../rpcclient/rpcclient/protos/ --c_out=../rpcserver/protos/