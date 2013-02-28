
cdef extern from "trans.h":
    int trans_create_blob( char *infile,  char *outfile, unsigned char *digest) 
    int TRANS_OK

cdef extern from "openssl/sha.h":
    int SHA_DIGEST_LENGTH

cimport stdlib

hex_chars = 'abcdef1234567890'

import os
import random
def create_blob(bytes infile, bytes outfile):
    cdef unsigned char *digest
    cdef char *c_infile = infile
    cdef char *c_outfile 
    cdef int status
    py_string = None
    if not os.path.exists(infile):
        raise IOError('%s does not exist' % infile)
        
    if not outfile:
        dirname = os.path.dirname(infile)
        tmpname = ''.join([random.choice(hex_chars) for i in xrange(20)])
        tmpfile = os.path.join(dirname,tmpname)
        c_outfile = tmpfile
    else:
        c_outfile = outfile

    try:
        digest = <unsigned char *>stdlib.malloc(SHA_DIGEST_LENGTH)
        status = trans_create_blob(c_infile, c_outfile, digest)
        if not status == TRANS_OK:
            raise IOError('Error creating blob')
        py_string = ''.join('%02x' % digest[i] for i in xrange(SHA_DIGEST_LENGTH))
    finally:
        stdlib.free(digest)
    return py_string


    

