#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>
#include <errno.h>
#include <openssl/sha.h>
#include <time.h>
#include <sys/time.h>
#include <zlib.h>
#include "trans.h"



int trans_tmp_file(char *filename, size_t len) {
    srand(time(NULL));
    char *hex_alphabet = "abcdef0123456789";
    size_t slen = 16;
    int fd;

    for(int i=0;i<len;i++) {
        filename[i] = hex_alphabet[ rand() % slen];
    }
    fd = open(filename, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    return fd;
}



int trans_create_blob(const char *infile, const char *outfile, unsigned char *digest) {
    int fd_in, fd_out;
    char buffer[TRANS_FILE_READ_BUFFER];
    char zbuffer[Z_CHUNK_SIZE];
    int zstatus;
    char temp_filename[40];
    size_t bytes_read=0;
    z_stream strm;
    SHA_CTX ctxt;
    bzero(&strm, sizeof(z_stream));

    strm.next_in = (Bytef *)buffer;
    SHA_Init(&ctxt);

    if(deflateInit2(&strm,  
                Z_DEFAULT_COMPRESSION, 
                Z_DEFLATED,
                GZIP_WINDOW | GZIP_ENCODING,
                8,
                Z_DEFAULT_STRATEGY)<0) {

        TRANS_ERROR(TRANS_GZIP_ERROR, "Failed to initialize deflate");
    }
    if((fd_in = open(infile, O_RDONLY))<0) {
        TRANS_ERROR(TRANS_FILE_ERROR, "Failed to open input file for reading");
    }
    if(outfile == NULL) { /* Make temp */
        fd_out = trans_tmp_file(temp_filename,40);
        if(fd_out < 0) {
            TRANS_ERROR(TRANS_FILE_ERROR, "Failed to create temporary file");
        }
        printf("Temp file: %s\n", temp_filename);
    }
    else {
        if((fd_out = open(outfile, O_WRONLY | O_CREAT | O_TRUNC, 0644))<0) {
            TRANS_ERROR(TRANS_FILE_ERROR, "Failed to open output file for writing");
        }
    }
    if(!outfile)
        printf("Temp file: %s\n", temp_filename);

    while((bytes_read = read(fd_in, buffer, TRANS_FILE_READ_BUFFER))>0) {
        SHA1_Update(&ctxt, buffer, bytes_read);
        strm.avail_out = Z_CHUNK_SIZE;
        strm.next_out = (Bytef *)zbuffer;
        strm.avail_in = bytes_read;
        zstatus = deflate(&strm, Z_NO_FLUSH);
        if(zstatus != Z_OK) {
            TRANS_ERROR(TRANS_GZIP_ERROR, "Failed to deflate file buffer");
        }
        if(write(fd_out, zbuffer, Z_CHUNK_SIZE - strm.avail_out) < 0) {
            TRANS_ERROR(TRANS_FILE_ERROR, "Failed to write gzip buffer");
        }
    }
    strm.avail_out = Z_CHUNK_SIZE;
    strm.next_out = (Bytef *)zbuffer;
    zstatus = deflate(&strm, Z_FINISH);
    if(zstatus != Z_STREAM_END)
        return TRANS_GZIP_ERROR;

    if(write(fd_out,zbuffer,Z_CHUNK_SIZE - strm.avail_out) < 0)  {
        TRANS_ERROR(TRANS_FILE_ERROR, "Failed to write the final gzip buffer");
    }

    if(!outfile)
        printf("Temp file: %s\n", temp_filename);
    SHA1_Final(digest, &ctxt);
    deflateEnd(&strm);
    close(fd_in);
    close(fd_out);
    if(outfile == NULL) { 
        printf("Temp file: %s\n", temp_filename);
        char str_digest[40];
        for(int i=0;i<SHA_DIGEST_LENGTH;i++) {
            snprintf(str_digest+(i*2), SHA_DIGEST_LENGTH - (i*2), "%02x", digest[i]);
        }
        if(rename(temp_filename, str_digest)<0) {
            printf("%s\n", strerror(errno));
            printf("%s\n", temp_filename);
            printf("%s\n", str_digest);
            TRANS_ERROR(TRANS_FILE_ERROR, "Failed to rename the file");
        }
        printf("Renamed to %s\n", str_digest);
    }

    return TRANS_OK;
}



int main(int argc, char *argv[]) {
    if((argc < 2) || (argc > 3)) {
        printf("Usage: sha_file <in> [<out>]\n");
        return 1;
    }
    unsigned char digest[SHA_DIGEST_LENGTH];
    int status;
    if(argc == 2) {
        status = trans_create_blob(argv[1],NULL,digest);
    }
    else
        status = trans_create_blob(argv[1], argv[2], digest);
    if(status != TRANS_OK) {
        printf("There was a problem: %s\n", trans_error);
        return 1;
    }

    for(int i=0;i<SHA_DIGEST_LENGTH;i++)
        printf("%02x", digest[i]);
    printf("\n");

    return 0;
}

    
