""" KlopPy is a Python package providing deserializers for soccer tracking- and event data, and
standardized data models designed to make working with different tracking- and event data like
a breeze. It aims to be the fundamental building blocks for loading tracking- and event data.

Here are just a few of the things that kloppy does well:
- Understandable standardized models for tracking- and event datasets
- Out-of-the-box deserializing tracking- and event data from different source into standardized models
- Flexible pitch dimensions transformer for changing a dataset pitch dimensions from one to another (eg OPTA's 100x100 -> TRACAB meters)
- Intelligent orientation transforming orientation of a dataset (eg from TRACAB fixed orientation to "Home Team" orientation)
"""

DOCLINES = (__doc__ or '').split("\n")
from distutils.core import setup

import setuptools

with open('README.md', 'r', encoding='utf8') as f:
    readme = f.read()

setup(
    name='kloppy',
    version='0.2.0',
    author='Koen Vossen',
    author_email='info@koenvossen.nl',
    url="https://github.com/PySport/kloppy",
    packages=setuptools.find_packages(exclude=["test"]),
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    description="Standardizing soccer tracking- and event data",
    long_description="\n".join(DOCLINES),
    python_requires='>=3.7',
    install_requires=[
        'lxml>=4.5.0'
    ],
    extras_require={
        'dev': [
            'pytest'
        ]
    }
)
