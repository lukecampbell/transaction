#!/usr/bin/env python

class BlobCorruption(IOError):
    pass

class TreeCorruption(IOError):
    pass

class TransactionCorruption(IOError):
    pass

class TransactionIndexError(IOError):
    pass

class RepositoryError(Exception):
    pass
