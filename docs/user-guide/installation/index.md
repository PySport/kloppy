# Installation

Before you can use kloppy, you'll need to get it installed. This guide will guide you to a minimal installation that'll work while you walk through the user guide.

## Install Python

Being a Python library, kloppy requires Python. Currently, kloppy supports Python version 3.9 — 3.12. Get the latest version of Python at [python.org](https://www.python.org/downloads/) or with your operating system's package manager.

You can verify that Python is installed by typing `python` from your shell; you should see something like:

```
Python 3.x.y
[GCC 4.x] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

## Install kloppy

You've got two options to install kloppy.

### Installing an official release with `pip`

This is the recommended way to install kloppy. Simply run this simple command in your terminal of choice:

```console
$ python -m pip install kloppy
```

You might have to install pip first. The easiest method is to use the [standalone pip installer](https://pip.pypa.io/en/latest/installing/#installing-with-get-pip-py).

### Installing the development version

Kloppy is actively developed on GitHub, where the code is [always available](https://github.com/PySport/kloppy). You can easily install the development version with:

```console
$ pip install git+https://github.com/PySport/kloppy.git
```

However, to be able to make modifications in the code, you should either clone the public repository:

```console
$ git clone git://github.com/PySport/kloppy.git
```

Or, download the [zipball](https://github.com/PySport/kloppy/archive/master.zip):

```console
$ curl -OL https://github.com/PySport/kloppy/archive/master.zip
```

Once you have a copy of the source, you can embed it in your own Python package, or install it into your site-packages easily:

```console
$ cd kloppy
$ python -m pip install -e .
```

## Verifying

To verify that kloppy can be seen by Python, type `python` from your shell. Then at the Python prompt, try to import kloppy:

```python
>>> import kloppy
>>> print(kloppy.__version__)
```
