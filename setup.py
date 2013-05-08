try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='dimagi-test-utils',
    version='1.0.0',
    description='Shared testing utilities',
    author='Dimagi',
    author_email='dev@dimagi.com',
    url='http://github.com/dimagi/test-utils',
    packages=['dimagitest'],
    license='MIT',
    install_requires=[
        'couchdbkit',
    ],
    tests_require=[
        'unittest2'
    ]
)
