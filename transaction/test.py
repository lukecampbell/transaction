#!/usr/bin/env python

from hashlib import sha1

from transaction import Transaction, TransactionBlob, TransactionTree, TransactionLog, TransactionRepository

from errors import BlobCorruption, TreeCorruption, TransactionCorruption, RepositoryError, TransactionIndexError

import gzip
import os
import unittest
from nose.plugins.attrib import attr

index = '.index'
class TransactionTest(unittest.TestCase):
    def tearDown(self):
        if os.path.exists(index):
            import shutil
            shutil.rmtree(index)

    def make_fake_data(self, filepath):
        message = '''
this is some really fake data
that was a line feed.

Here's some funky values \x12 \x00 \xF3'''
        
        with open(filepath,'w') as f:
            f.write(message)
        return sha1(message).hexdigest()

class TestBlob(TransactionTest):
        
    @attr('short')
    def test_simple_blob(self):
        test_file = './test_file'
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
        self.assertTrue(os.path.exists(test_file))
        with open(test_file, 'r') as f:
            buf = f.read()
        self.assertEquals(sha1(buf).hexdigest(), sample_sha)



    @attr('ext')
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

    @attr('short')
    def test_integrity_crash(self):
        good_file = './gf'
        with open(good_file,'w') as f:
            f.write('this is some data that will get compressed.')
        self.addCleanup(os.remove,good_file)

        tb = TransactionBlob(index,good_file)
        tb.add_to_index()
        with open(os.path.join(index, tb.sha_hash),'a') as f:
            f.write('This will screw up the gzip inflation')


        self.assertRaises(BlobCorruption, tb.read_from_index, index, tb.sha_hash, good_file)

        tb.add_to_index()
        with gzip.open(os.path.join(index,tb.sha_hash),'a') as f:
            f.write('This will screw up the sha')

        self.assertRaises(BlobCorruption, tb.read_from_index, index, tb.sha_hash, good_file)

        


class TestTree(TransactionTest):
    @attr('short')
    def test_add_to_index(self):
        file1 = './file1'
        file2 = './file2'
        self.make_fake_data(file1)
        self.addCleanup(os.remove,file1)
        self.make_fake_data(file2)
        self.addCleanup(os.remove,file2)

        tt = TransactionTree(index)
        tb1 = TransactionBlob(index, file1)
        tb2 = TransactionBlob(index, file2)

        tt.add(tb1)
        tt.add(tb2)

        self.assertEquals(tb1.sha_hash, tb2.sha_hash)
        self.assertTrue(os.path.exists(os.path.join(index, tb1.sha_hash)))

        tt.add_to_index()
        self.assertTrue(os.path.exists(os.path.join(index,tt.sha_hash)))

        tt2 = TransactionTree.read_from_index(index,tt.sha_hash)
        self.assertEquals(tt._tree, tt2._tree)

        os.remove(file1)
        os.remove(file2)
        
        tt2.apply()

        self.assertTrue(os.path.exists(file1))
        self.assertTrue(os.path.exists(file2))

class TestLog(TransactionTest):
    @attr('short')
    def test_log(self):
        log = TransactionLog(index)
        tree = TransactionTree(index)

        repo = TransactionRepository(index)
        log.add(tree, repo)

        file1 = './file1'
        file2 = './file2'
        self.make_fake_data(file1)
        self.addCleanup(os.remove,file1)
        self.make_fake_data(file2)
        self.addCleanup(os.remove,file2)
        
        tb1 = TransactionBlob(index, file1)
        tb2 = TransactionBlob(index, file2)
        tree2 = TransactionTree(index)
        tree2.add(tb1)
        tree2.add(tb2)

        log.add(tree2, repo)

        self.assertEquals(log._log[0][0], tree.sha_hash)
        self.assertEquals(log._log[1][0], tree2.sha_hash)


class TestRepository(TransactionTest):
    @attr('short')
    def test_basic_repo(self):
        file1 = './file1'
        file2 = './file2'
        self.make_fake_data(file1)
        self.addCleanup(os.remove,file1)
        self.make_fake_data(file2)
        self.addCleanup(os.remove,file2)
        
        tb1 = TransactionBlob(index, file1)
        tb2 = TransactionBlob(index, file2)

        repo = TransactionRepository(index)
        repo.add_blob(tb1)
        repo.add_blob(tb2)

        self.assertEquals(repo.blobs[tb1.sha_hash], 2)

        repo.delete_blob(tb1)

        self.assertEquals(repo.blobs[tb1.sha_hash], 1)

        repo.delete_blob(tb1)

        self.assertFalse(os.path.exists(os.path.join(index, tb1.sha_hash)))



class TestTransaction(TransactionTest):
    pass

