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

from errors import BlobCorruption, TreeCorruption, TransactionCorruption, RepositoryError, TransactionIndexError, RepositoryCorruption


class TransactionObject:
    def __init__(self, index_path):
        self.index_path = cas(index_path)
        self.sha_hash   = None

class TransactionBlob(TransactionObject):
    '''
    Binary data object in the index

    Concept from Linus Torvalds, implementation concept from David Stuebe
    '''
    def __init__(self,index_path,filepath):
        TransactionObject.__init__(self, index_path)
        self.filepath   = ''
        if not os.path.exists(filepath):
            raise IOError("Can't read %s" % filepath)
        self.filepath   = filepath

    def add_to_index(self):
        filename = os.path.basename(self.filepath)
        
        self.sha_hash = create_blob(self.filepath, os.path.join(self.index_path, filename))
        os.rename(os.path.join(self.index_path, filename), os.path.join(self.index_path, self.sha_hash))

    @classmethod
    def read_from_index(cls, index_path, sha_hash, filepath):
        data_sha = sha1()
        if not os.path.exists(os.path.join(index_path, sha_hash)):
            raise IOError("No such file %s" % os.path.join(index_path, sha_hash))
        try:
            with gzip.open(os.path.join(index_path, sha_hash), 'r') as gz_f:
                with open(filepath,'w') as out:
                    data =1
                    while data:
                        data = gz_f.read(1024 * 512)
                        data_sha.update(data)
                        out.write(data)
        except IOError as e:
            raise BlobCorruption(e)
        data_sha = data_sha.hexdigest()
        if not data_sha == sha_hash:
            raise BlobCorruption('Data integrity compromised')
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
        instance = cls(index_path, filepath)
        instance.sha_hash = sha_hash
        instance.index_path = index_path
        return instance


class TransactionTree(TransactionObject):
    def __init__(self, index_path):
        self._tree      = {}
        TransactionObject.__init__(self, index_path)

    def add(self, blob):
        if blob.sha_hash is None:
            blob.add_to_index()
        self._tree[blob.filepath] = blob.sha_hash

    def add_to_index(self):
        data = msgpack.packb(self._tree)
        self.sha_hash = self.hash_me(data)
        with gzip.open(os.path.join(self.index_path, self.sha_hash), 'w') as gz_f:
            gz_f.write(data)

    @classmethod
    def read_from_index(cls, index_path, sha_hash):
        data = None
        with gzip.open(os.path.join(index_path,sha_hash),'r') as gz_f:
            data = gz_f.read()

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
        for path,sha in self._tree.iteritems():
            TransactionBlob.read_from_index(self.index_path, sha, path)

    @classmethod
    def hash_me(cls, data):
        sha_hash = sha1('tree %s\0%s' % (len(data), data)).hexdigest()
        return sha_hash



class TransactionLog(TransactionObject):
    def __init__(self, index_path):
        TransactionObject.__init__(self, index_path)
        self._log       = []
        self.log_path = os.path.join(self.index_path,'log')
        if os.path.exists(self.log_path):
            with open(self.log_path, 'r') as f:
                self._log = list(msgpack.unpackb(f.read()))

    def add(self,tree,repo):
        if tree.sha_hash is None:
            tree.add_to_index()
        if repo.sha_hash is None:
            repo.add_to_index()
        self._log.append((tree.sha_hash, repo.sha_hash, time.time()))
        with open(self.log_path,'w') as f:
            f.write(msgpack.packb(self._log))

    def __repr__(self):
        return repr(self._log)


class Transaction(TransactionObject):
    
    def __init__(self, root):
        TransactionObject.__init__(self, '.index')

        self.root = root
        self.log = TransactionLog(self.index_path)

    def add_to_index(self):
        tree = TransactionTree(self.index_path)
        repo = TransactionRepository(self.index_path)
        for root, dirs, files in os.walk(self.root):
            if '.index' in root: continue
            for f in files:
                tb = TransactionBlob(self.index_path,os.path.join(root,f))
                tree.add(tb)
                repo.add_blob(tb)
        tree.add_to_index()
        repo.add_to_index()
        self.log.add_tree(tree, repo)
        data = '%s %s' %(tree.sha_hash, repo.sha_hash)
        data_hash = self.hash_me(data)
        with open(os.path.join(self.index_path,data_hash),'w') as f:
            f.write(data)

        with open(os.path.join(self.index_path,'HEAD'),'w') as f:
            f.write(data_hash)

    @classmethod
    def read_from_index(cls,index_path,sha):
        data = None
        with open(os.path.join(index_path,sha),'r') as f:
            data = f.read()
        if cls.hash_me(data) != sha:
            raise TransactionCorruption('The transaction integrity is compromised')
        tree_hash, repo_hash = data.split()
        
        tree = TransactionTree.read_from_index(index_path,tree_hash)
        tree.apply()

        inst = cls(index_path)
        inst.sha_hash = sha
        return inst

    @classmethod
    def remove_transaction(cls, index_path, sha):
        pass

        



    @property
    def HEAD(self):
        data = None
        with open(os.path.join(self.index_path,'HEAD'),'r') as f:
                data = f.read()
        return data

    @classmethod
    def hash_me(cls, data):
        data = 'commit %s\0%s' %(len(data),data)
        return sha1(data).hexdigest()


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

class TransactionRepository(TransactionObject):
    def __init__(self, index_path):
        TransactionObject.__init__(self, index_path)
        self.blobs = {}

    def add_to_index(self):
        data = msgpack.packb(self.blobs)
        self.sha_hash = self.hash_me(data)
        with gzip.open(os.path.join(self.index_path, self.sha_hash), 'w') as gz_f:
            gz_f.write(data)

    @classmethod
    def read_from_index(cls, index_path, sha_hash):
        data = None
        with gzip.open(os.path.join(index_path, sha_hash)) as gz_f:
            data = gz_f.read()
        data_hash = cls.hash_me(data)
        if not data_hash == sha_hash:
            raise RepositoryCorruption('The Repository integrity is compromised')
        
        blobs = msgpack.unpackb(data)
        inst = cls(index_path)
        inst.blobs = blobs
        inst.sha_hash = sha_hash
        return inst


    def add_blob(self, blob):
        if blob.sha_hash is None:
            blob.add_to_index()
        if not os.path.exists(os.path.join(self.index_path, blob.sha_hash)):
            raise TransactionIndexError('Missing from index: %s\t%s' % ( blob.sha_hash, blob.filepath))
        if blob.sha_hash not in self.blobs:
            self.blobs[blob.sha_hash] = 1
        else:
            self.blobs[blob.sha_hash] += 1

    def delete_blob(self, blob):
        if blob.sha_hash not in self.blobs:
            raise RepositoryError('Blob %s not tracked by repository' % blob.sha_hash)
        self.blobs[blob.sha_hash]-= 1
        if self.blobs[blob.sha_hash] < 1:
            del self.blobs[blob.sha_hash]
            os.remove(os.path.join(self.index_path, blob.sha_hash))
    
    @classmethod
    def hash_me(cls, data):
        data = 'repo %s\0%s' %(len(data), data)
        return sha1(data).hexdigest()

def cas(path):
    if not os.path.exists(path):
        os.mkdir(path)
    return path

