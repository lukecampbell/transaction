try:
    from setuptools import setup, find_packages
    packages = find_packages()
except ImportError:
    from distutils import setup
    packages = ['transaction']
from distutils.extension import Extension

# setuptools DWIM monkey-patch madness
# http://mail.python.org/pipermail/distutils-sig/2007-September/thread.html#8204
import sys

if 'setuptools.extension' in sys.modules:
    m = sys.modules['setuptools.extension']
    m.Extension.__dict__ = m._Extension.__dict__
bindings_extension = Extension("transaction.bindings", ["transaction/bindings.pyx", 'transaction/trans_blob.c'], libraries=['ssl','z','crypto'] )


classifiers = ''' Intended Audience :: Science/Research
Intended Audience :: Developers
Intended Audience :: Education
Operating System :: OS Independent
Programming Language :: Python
Topic :: Scientific/Engineering
Topic :: Education
Topic :: Software Development :: Libraries :: Python Modules'''
setup(name = 'transaction', 
        version='0.0.1',
        description='Transactional file system',
        long_description=open('README.md').read(),
        license='LICENSE.txt',
        author='Luke Campbell',
        author_email='luke.s.campbell@gmail.com',
        url='https://github.com/lukecampbell/transaction/',
        ext_modules=[bindings_extension],
        classifiers=classifiers.split('\n'),
        packages=packages,
        keywords=[],
        setup_requires=[
            'setuptools_cython',
            'msgpack-python==0.1.13',
            ],
        )



