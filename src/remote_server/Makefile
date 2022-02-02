SERVER_CC=gcc

all: server 

common_server.o: common.c
	$(SERVER_CC) $(SERVER_CFLAGS) -c common.c -o common_server.o

server: server.c common_server.o
	$(SERVER_CC) $(SERVER_CFLAGS) -Wno-unguarded-availability-new server.c -lpthread -ldl common_server.o -o server

clean:
	rm -rf *.o server
