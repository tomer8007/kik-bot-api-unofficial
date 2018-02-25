from codecs import open
from os import path

from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='kik_unofficial',

    version='0.2.1',

    description='Python API for writing unoffical kik bots that act like humans',
    long_description=long_description,

    url='https://github.com/tomer8007/kik-bot-api-unofficial',
    download_url="https://github.com/tomer8007/kik-bot-api-unofficial/tarball/master",

    author='Tomer',
    author_email='tomer8007@gmail.com',

    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
    ],

    keywords=['kik', 'bot', 'kikbot', 'kik-messenger-platform', 'api', 'unofficial', 'python',],

    packages=find_packages(exclude=['docs', 'test']),

    install_requires=['pbkdf2', 'rsa', 'lxml', 'bs4', 'protobuf'],

    extras_require={
        'dev': [],
        'test': [],
    },

    package_data={
        'kik_unofficial': [],
    },

    entry_points={
        'console_scripts': [
            'kikapi=kik_unofficial.cmdline:execute',
        ],
    },
)
