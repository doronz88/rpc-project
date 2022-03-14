SERVER_CC=gcc
LDFLAGS=
UNAME_S:=$(shell uname -s)

ifeq ($(UNAME_S),Darwin)
	LDFLAGS += -framework CoreFoundation
endif

all: rpcserver 

common.o: common.c
	$(SERVER_CC) $(SERVER_CFLAGS) -c common.c -o common.o

rpcserver: rpcserver.c common.o
	$(SERVER_CC) $(SERVER_CFLAGS) $(LDFLAGS) -Wno-unguarded-availability-new rpcserver.c -lpthread -ldl common.o -o rpcserver

clean:
	rm -rf *.o rpcserver
