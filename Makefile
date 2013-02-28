CC=gcc
LDFLAGS=  -lssl -lcrypto -lz
CPPFLAGS= -std=c99 -Wall -g -ggdb 
OBJECTS=transaction/trans_blob.o

trans_blob: $(OBJECTS)
	$(CC) -o $@ $(LDFLAGS) $(OBJECTS)

$(OBJETS): %.o: %.c
	$(CC) -o $@ $(CPPFLAGS) $<

clean:
	rm -rf *.o
	rm -rf sha_file
