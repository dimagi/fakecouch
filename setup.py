try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import sys

install_requires = ['couchdbkit']

if sys.version_info[1] < 7:
    install_requires.append('ordereddict')

setup(
    name='fakecouch',
    version='0.0.1',
    description='Fake implementation of CouchDBKit api for testing purposes',
    author='Dimagi',
    author_email='dev@dimagi.com',
    url='http://github.com/dimagi/fakecouch',
    py_modules=['fakecouch'],
    test_suite='tests',
    test_loader='unittest2:TestLoader',
    license='MIT',
    install_requires=install_requires,
    tests_require=[
        'unittest2'
    ]
)
