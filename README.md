# kloppy: standardizing soccer tracking and event data <a href='https://kloppy.pysport.org'><img style="width: 120px; height: 139px" src="https://github.com/PySport/kloppy/raw/master/docs/logo.png" align="right" /></a>
> klop·pen (klopte, heeft geklopt) - juist zijn; overeenkomen, uitkomen met: *dat klopt, dat kan kloppen* is juist; *dat klopt als een zwerende vinger* dat is helemaal juist

[![PyPI Latest Release](https://img.shields.io/pypi/v/kloppy.svg)](https://pypi.org/project/kloppy/)
[![Downloads](https://pepy.tech/badge/kloppy/month)](https://pepy.tech/project/kloppy/month)
![](https://img.shields.io/github/license/PySport/kloppy)
![](https://img.shields.io/pypi/pyversions/kloppy)
[![Powered by PySport](https://img.shields.io/badge/powered%20by-PySport-orange.svg?style=flat&colorA=104467&colorB=007D8A)](https://pysport.org)

## What is it?

Each vendor of soccer data uses its own unique format to describe the course of a game. Hence, software written to analyze this data has to be tailored to a specific vendor and cannot be used without modifications to analyze data from other vendors. Kloppy is a Python package that addresses the challenges posed by the variety of data formats and aims to be the fundamental building block for processing soccer tracking and event data. It provides (de)serializers, standardized data models, filters, and transformers which make working with tracking and event data from different vendors a breeze.

## Main features

Here are just a few of the things that kloppy does well:

#### Loading data
- Load **public datasets** to get started right away
- Understandable **standardized data models** for tracking and event data
- Out-of-the-box **(de)serializing** tracking and event data from different vendors into standardized models and vice versa

#### Processing data
- Flexibly transform a dataset's **pitch dimensions** from one format to another (e.g., from OPTA's 100x100 to TRACAB meters)
- Transform the **orientation** of a dataset (e.g., from TRACAB fixed orientation to "Home Team" orientation)

#### Pattern matching
- Search for **[complexe patterns](https://github.com/PySport/kloppy/examples/pattern_matching/repository/README.md)** in event data
- Use `kloppy-query` to export fragments to XML file


## Where to get it

The source code is currently hosted on GitHub at: [https://github.com/PySport/kloppy](https://github.com/PySport/kloppy).

Installers for the latest released version are available at the [Python package index](https://pypi.org/project/kloppy).

```sh
pip install kloppy
```

## Documentation

The official documentation is hosted on pysport.org: [https://kloppy.pysport.org](https://kloppy.pysport.org). 


## Contributing to kloppy

All contributions, bug reports, bug fixes, documentation improvements, enhancements, and ideas are welcome.

An overview on how to contribute can be found in the **[contributing guide](https://kloppy.pysport.org/contributing)**.

If you are simply looking to start working with the kloppy codebase, navigate to the GitHub "issues" tab and start looking through interesting issues.
