from distutils.core import setup

with open('README.md', 'r', encoding='utf8') as f:
    readme = f.read()

setup(
    name='KlopPy',
    version='0.1',
    author='Koen Vossen',
    author_email='info@koenvossen.nl',
    url="https://github.com/PySport/kloppy",
    packages=['kloppy',],
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    description="Standardizing soccer tracking- and event data",
    long_description=readme,
)