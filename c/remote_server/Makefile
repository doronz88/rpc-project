SERVER_CC=gcc
CLIENT_CC=gcc

all: server client

common_server.o: common.c
	$(SERVER_CC) $(SERVER_CFLAGS) -c common.c -o common_server.o

common_client.o: common.c
	$(CLIENT_CC) $(CLIENT_CFLAGS) -c common.c -o common_client.o

server: server.c common_server.o
	$(SERVER_CC) $(SERVER_CFLAGS) server.c common_server.o -o server

client: client.c common_client.o
	$(CLIENT_CC) $(CLIENT_CFLAGS) client.c common_client.o -o client

clean:
	rm -rf *.o client server
