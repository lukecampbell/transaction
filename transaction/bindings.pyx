
cdef extern from "trans.h":
    int trans_create_blob( char *infile,  char *outfile, unsigned char *digest) 


def create_blob(str infile, str outfile):
    pass
