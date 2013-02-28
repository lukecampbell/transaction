#!/usr/bin/env python
'''
@author Luke Campbell
@file ion/services/dm/utility/transaction.py
'''

from hashlib import sha1
from bindings import create_blob
import os
import zlib
import gzip
import msgpack
import time

from errors import BlobCorruption, TreeCorruption, TransactionCorruption, RepositoryError, TransactionIndexError


class TransactionBlob:
    '''
    Binary data object in the index

    Concept from Linus Torvalds, implementation concept from David Stuebe
    '''
    def __init__(self,index_path,filepath):
        self.filepath   = ''
        self.sha_hash   = None
        self.index_path = None
        if not os.path.exists(filepath):
            raise IOError("Can't read %s" % filepath)
        self.filepath   = filepath
        self.index_path = cas(index_path)

    def add_to_index(self):
        filename = os.path.basename(self.filepath)
        
        self.sha_hash = create_blob(self.filepath, os.path.join(self.index_path, filename))
        os.rename(os.path.join(self.index_path, filename), os.path.join(self.index_path, self.sha_hash))

    @classmethod
    def read_from_index(cls, index_path, sha_hash, filepath):
        data = None
        with gzip.open(os.path.join(index_path, sha_hash),'r') as f:
            data = f.read()
        data_sha = sha1(data).hexdigest()
        if not data_sha == sha_hash:
            raise BlobCorruption('Data integrity compromised')
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
        with open(filepath, 'w') as f:
            f.write(data)
        instance = cls(index_path, filepath)
        instance.sha_hash = sha_hash
        instance.index_path = index_path
        return instance


class TransactionTree:
    def __init__(self, index_path):
        self._tree      = {}
        self.sha_hash   = None
        self.index_path = None
        self.index_path = cas(index_path)

    def add(self, blob):
        if blob.sha_hash is None:
            blob.add_to_index()
        self._tree[blob.sha_hash] = blob.filepath

    def add_to_index(self):
        data = zlib.compress(msgpack.packb(self._tree))
        sha_hash = self.hash_me(data)
        with open(os.path.join(self.index_path, sha_hash),'w') as f:
            f.write(data)
        self.sha_hash = sha_hash

    @classmethod
    def read_from_index(cls, index_path, sha_hash):
        data = None
        with open(os.path.join(index_path, sha_hash),'r') as f:
            data = zlib.decompress(f.read())
        data_hash = cls.hash_me(data)
        if not data_hash == sha_hash:
            raise TreeCorruption('The Tree integrity is compromised')

        tree = msgpack.unpackb(data)
        instance = cls(index_path)
        instance._tree = tree
        instance.index_path = index_path
        instance.sha_hash = sha_hash
        return instance

    def apply(self):
        for sha,path in self._tree.iteritems():
            TransactionBlob.read_from_index(self.index_path, sha, path)

    @classmethod
    def hash_me(cls, data):
        sha_hash = sha1('tree %s\0%s' % (len(data), data)).hexdigest()
        return sha_hash



class TransactionLog:
    def __init__(self, index_path):
        self._log       = []
        self.index_path = None
        self.log_path   = None
        self.index_path = cas(index_path)
        self.log_path = os.path.join(self.index_path,'log')
        if os.path.exists(self.log_path):
            with open(self.log_path, 'r') as f:
                self._log = list(msgpack.unpackb(f.read()))

    def add_tree(self,tree):
        self._log.append((tree.sha_hash, time.time()))
        with open(self.log_path,'w') as f:
            f.write(msgpack.packb(self._log))

    def __repr__(self):
        return repr(self._log)


class Transaction:
    
    def __init__(self, root):
        self.log        = None
        self.index_path = None
        self.root = root
        self.index_path = cas(os.path.join(root,'.index'))
        if not os.path.exists(self.index_path):
            os.mkdir(self.index_path)
        self.log = TransactionLog(self.index_path)

    def commit(self):
        tree = TransactionTree(self.index_path)
        for root, dirs, files in os.walk(self.root):
            if '.index' in root: continue
            for f in files:
                tb = TransactionBlob(self.index_path,os.path.join(root,f))
                tree.add(tb)
        tree.add_to_index()
        self.log.add_tree(tree)
        with open(os.path.join(self.index_path,'HEAD'),'w') as f:
            f.write(tree.sha_hash)

    def checkout(self,sha):
        tree = TransactionTree.read_from_index(self.index_path,sha)
        tree.apply()
        with open(os.path.join(self.index_path,'HEAD'),'w') as f:
            f.write(tree.sha_hash)

    @property
    def HEAD(self):
        data = None
        with open(os.path.join(self.index_path,'HEAD'),'r') as f:
                data = f.read()
        return data


    def check_integrity(self):
        # If the log is empty or None, no integrity to check
        if not self.log._log:
            return
        sha, ts = self.log._log[-1]
        try:
            head = self.HEAD
        except IOError:
            raise TransactionCorruption('No HEAD, recommend reverting to latest commit in logs')
        if not head == sha:
            raise TransactionCorruption('Transaction integrity compromised')

class TransactionRepository:
    def __init__(self, index_path):
        self.blobs = {}
        self.index_path = index_path

    def add_blob(self, blob):
        if not os.path.exists(os.path.join(self.index_path, blob.sha_hash)):
            raise TransactionIndexError('Missing from index: %s\t%s' % ( blob.sha_hash, blob.filepath))
        self.blobs[blob.sha_hash] = 1

    def delete_blob(self, blob):
        if blob.sha_hash not in self.blobs:
            raise RepositoryError('Blob %s not tracked by repository' % blob.sha_hash)
        self.blobs[blob.sha_hash]-= 1
        if self.blobs[blob.sha_hash] < 1:
            del self.blobs[blob.sha_hash]
            os.remove(os.path.join(self.index_path, blob.sha_hash))


def cas(path):
    if not os.path.exists(path):
        os.mkdir(path)
    return path

