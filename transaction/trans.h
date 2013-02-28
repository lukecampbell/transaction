#ifndef __sha_file_h__
#define __sha_file_h__

#ifndef TRANS_FILE_READ_BUFFER
#define TRANS_FILE_READ_BUFFER 2097152
#endif

#ifndef Z_CHUNK_SIZE
#define Z_CHUNK_SIZE 0x4000
#endif

#ifndef GZIP_ENCODING
#define GZIP_ENCODING 16
#endif

#ifndef GZIP_WINDOW
#define GZIP_WINDOW 15
#endif 

#define TRANS_OK          0
#define TRANS_GZIP_ERROR -2
#define TRANS_FILE_ERROR -3

static char *trans_error=NULL;

#define TRANS_ERROR(code,message) \
    trans_error = message; \
    return code;

int trans_create_blob(const char *infile, const char *outfile, unsigned char *digest); 
int trans_tmp_file(char *filename, size_t len);
#endif /*__sha_file_h__ */
