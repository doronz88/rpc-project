CC=gcc

common: common.c
	$(CC) $(CFLAGS) -c common.c -o common.o

server: server.c common.o
	$(CC) $(CFLAGS) server.c common.o -o server

client: client.c common.o
	$(CC) $(CFLAGS) client.c common.o -o client

clean:
	rm -rf .o client server

all: server client
