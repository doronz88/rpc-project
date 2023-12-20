PROTO_FILES = rpc.proto
PYTHON_OUT_DIR=../rpcclient/rpcclient/protos/
C_OUT_DIR=../rpcserver/protos/

.PHONY: all c_protos python_protos clean

all: c_protos python_protos

c_protos: $(PROTO_FILES)
	# Compile Protocol Buffers for C
	mkdir -p $(C_OUT_DIR)
	protoc --c_out=$(C_OUT_DIR) --proto_path=. $(PROTO_FILES)

python_protos: $(PROTO_FILES)
	# Compile Protocol Buffers for Python
	mkdir -p $(PYTHON_OUT_DIR)
	python3 -m grpc_tools.protoc --python_out=$(PYTHON_OUT_DIR) --mypy_out=$(PYTHON_OUT_DIR) --proto_path=. $(PROTO_FILES)

clean:
	# Clean up generated files
	rm -rf $(C_OUT_DIR) $(PYTHON_OUT_DIR)
