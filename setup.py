import setuptools
import builtins
from distutils.core import setup


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
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
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
            'dataclasses==0.8;python_version<"3.7"',
            'mypy_extensions;python_version<"3.8"',
            'typing_extensions;python_version<"3.8"',
            "python-dateutil>=2.8.1,<3",
        ],
        extras_require={
            "test": ["pytest>=6.2.5,<7", "pandas>=1.0.0,<2", "black==22.3.0"],
            "development": ["pre-commit==2.6.0"],
            "query": ["networkx>=2.4,<3"],
        },
    )


if __name__ == "__main__":
    setup_package()

    del builtins.__KLOPPY_SETUP__
