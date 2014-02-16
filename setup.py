import os
import re
from setuptools import setup


def get_version(package):
    """Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = 'django-deep-prefetch',
    version = get_version('deep_prefetch'),
    author = 'Andrew Pashkin',
    url = 'https://bitbucket.org/andrew_pashkin/django-deep-prefetch',
    author_email = 'andrew.pashkin@gmx.co.uk',
    description = ("Drop-in replacement for Django ``prefetch_related`` "
                   "which is able to prefetch GenericForeignKey's"),
    license = 'BSD',
    keywords = 'prefetch generic django cache orm gfk',
    packages=['deep_prefetch', 'tests'],
    long_description=read('README.rst'),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
    ],
)