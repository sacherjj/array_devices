
from __future__ import with_statement

# http://docs.python.org/distutils/
# http://packages.python.org/distribute/
try:
    from setuptools import setup
except:
    from distutils.core import setup

import os.path

setup(
    name = 'array_devices',
    description = 'Python Interface for Array Electronic Load',
    version = '1.0.2',
    long_description = '''This package is a Python-based interface for the Array 3710 Electronic Load.''',
    author = 'Joe Sacher',
    author_email = 'sacherjj@gmail.com',
    url = 'https://github.com/sacherjj/array_devices',
    download_url = 'http://github.com/sacherjj/array_devices/tarball/master',
    keywords = 'Array Electronic Load',
    license = 'MIT License',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Intended Audience :: Science/Research',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3'
        ],
    packages = ['array_devices'],
    requires = [],
    extras_require = {
        'serial': ['pyserial']
    }
)
