
cdef extern from "trans.h":
    int trans_create_blob(const char *infile, const char *outfile, unsigned char *digest) 


def create_blob(str infile, str outfile):
    pass
