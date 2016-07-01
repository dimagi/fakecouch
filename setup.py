try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='fakecouch',
    version='0.0.9',
    description='Fake implementation of CouchDBKit api for testing purposes',
    author='Dimagi',
    author_email='dev@dimagi.com',
    url='http://github.com/dimagi/fakecouch',
    py_modules=['fakecouch'],
    test_suite='tests',
    test_loader='unittest2:TestLoader',
    license='MIT',
    install_requires=[],
    tests_require=[
        'unittest2',
        'couchdbkit',
    ]
)
