# kloppy: standardizing soccer tracking- and event data <a href='https://kloppy.pysport.org'><img src="docs/logo.png" align="right" height="139"/></a>
> klop·pen (klopte, heeft geklopt) - juist zijn; overeenkomen, uitkomen met: dat klopt, dat kan kloppen is juist; dat klopt als een zwerende vinger dat is helemaal juist

[![PyPI Latest Release](https://img.shields.io/pypi/v/kloppy.svg)](https://pypi.org/project/kloppy/)
[![Downloads](https://pepy.tech/badge/kloppy/month)](https://pepy.tech/project/kloppy/month)
![](https://img.shields.io/github/license/PySport/kloppy)
![](https://img.shields.io/pypi/pyversions/kloppy)
[![Powered by PySport](https://img.shields.io/badge/powered%20by-PySport-orange.svg?style=flat&colorA=104467&colorB=007D8A)](https://pysport.org)
--------
## What is it?

**kloppy** is a Python package providing (de)serializers for soccer tracking- and event data,
standardized data models, filters, and transformers designed to make working with 
different tracking- and event data like a breeze. It aims to be the fundamental building blocks for loading, filtering and tranforming
 tracking- and event data.

## Main Features
Here are just a few of the things that kloppy does well:
#### Loading data
- Directly load **Public datasets** to get started right away. 
- Understandable **Standardized models** for tracking- and event datasets
- Out-of-the-box **(De)serializing** tracking- and event data from different sources into standardized models and vice versa
#### Processing data
- Flexible **pitch dimensions** transformer for changing a dataset pitch dimensions from one to another (eg OPTA's 100x100 -> TRACAB meters)
- Intelligent **orientation** transforming orientation of a dataset (eg from TRACAB fixed orientation to "Home Team" orientation)
#### Pattern matching
- Search for **complexe patterns**(examples/pattern_matching/repository/README.md) in event data.
- Use `kloppy-query` to export fragments to XML file


## Where to get it
The source code is currently hosted on GitHub at:
https://github.com/PySport/kloppy

Installers for the latest released version are available at the [Python
package index](https://pypi.org/project/kloppy).

```sh
# or PyPI
pip install kloppy
```

# Documentation

The official documentation is hosted on pysport.org: https://kloppy.pysport.org


# Contributing to kloppy
All contributions, bug reports, bug fixes, documentation improvements, enhancements, and ideas are welcome.

A overview on how to contribute can be found in the **[contributing guide](CONTRIBUTING.md)**.

If you are simply looking to start working with the kloppy codebase, navigate to the GitHub "issues" tab and start looking through interesting issues.


