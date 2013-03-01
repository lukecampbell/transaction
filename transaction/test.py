#!/usr/bin/env python

from hashlib import sha1

from transaction import Transaction, TransactionBlob, TransactionLog, TransactionRepository

from errors import BlobCorruption, TreeCorruption, TransactionCorruption, RepositoryError, TransactionIndexError

import gzip
import os
import unittest


index = '.index'
class TransactionTest(unittest.TestCase):
    pass

class TestBlob(TransactionTest):
    def tearDown(self):
        if os.path.exists(index):
            import shutil
            shutil.rmtree(index)
        
    def test_simple_blob(self):
        test_file = 'test_file'
        sample = 'this is a test \x12 \x00 <-- ugly bytes \xF2'
        sample_sha = sha1(sample).hexdigest()
        with open(test_file, 'w') as f:
            f.write(sample)
        self.addCleanup(os.remove,test_file)

        tb = TransactionBlob(index,test_file)
        tb.add_to_index()
        self.assertTrue(os.path.exists(os.path.join(index,sample_sha)))
        with gzip.open(os.path.join(index,sample_sha)) as f:
            self.assertEquals(f.read(), sample)

        os.remove(test_file)
        TransactionBlob.read_from_index(index, sample_sha, os.path.join('.',test_file))


    def test_large_blob(self):
        ugly_file = 'ugly'
        if not os.path.exists('/dev/urandom'):
            return

        sha = sha1()
        with open('/dev/urandom','r') as f_in: 
            with open(ugly_file, 'w') as f_out:
                while f_in.tell() < (1024*1024*64):
                    buf = f_in.read(1024*256)
                    sha.update(buf)
                    f_out.write(buf)


        self.addCleanup(os.remove,ugly_file)
        sha_hash = sha.hexdigest()

        tb = TransactionBlob(index, ugly_file)
        tb.add_to_index()

        self.assertTrue(os.path.exists(os.path.join(index,sha_hash)))

        tb.read_from_index(index, sha_hash, os.path.join('.',ugly_file))

        new_hash = sha1()
        with open(ugly_file,'r') as f:
            while f.tell() < os.stat(f.name).st_size:
                data = f.read(1024)
                new_hash.update(data)
        self.assertEquals(new_hash.hexdigest(), sha.hexdigest())

class TestLog(TransactionTest):
    pass

class TestRepository(TransactionTest):
    pass

class TestTransaction(TransactionTest):
    pass

