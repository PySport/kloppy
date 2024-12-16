import builtins
from distutils.core import setup

import setuptools

builtins.__KLOPPY_SETUP__ = True
import kloppy


def setup_package():
    with open("README.md", "r") as f:
        readme = f.read()

    setup(
        name="kloppy",
        version=kloppy.__version__,
        author="Koen Vossen",
        author_email="info@koenvossen.nl",
        url="https://kloppy.pysport.org/",
        packages=setuptools.find_packages(exclude=["tests"]),
        license="BSD",
        description="Standardizing soccer tracking- and event data",
        long_description=readme,
        long_description_content_type="text/markdown",
        classifiers=[
            "Intended Audience :: Developers",
            "Intended Audience :: Science/Research",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "License :: OSI Approved",
            "Topic :: Scientific/Engineering",
        ],
        entry_points={
            "console_scripts": ["kloppy-query = kloppy.cmdline:run_query"]
        },
        install_requires=[
            "lxml>=4.4.0,<5",
            "requests>=2.0.0,<3",
            "pytz>=2020.1",
            'typing_extensions;python_version<"3.11"',
            "sortedcontainers>=2",
        ],
        extras_require={
            "test": [
                "pytest>=6.2.5,<7",
                "pandas>=2",
                "black==22.3.0",
                "polars>=0.16.6",
                "pyarrow",
                "pytest-lazy-fixture",
                "s3fs",
                "moto[s3]",
                "pytest-httpserver",
            ],
            "development": ["pre-commit==2.6.0"],
            "query": ["networkx>=2.4,<3"],
        },
    )


if __name__ == "__main__":
    setup_package()

    del builtins.__KLOPPY_SETUP__
