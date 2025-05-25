# Code contribution guidelines

## Code standards

Writing good code is not just about what you write. It is also about how you write it. During Continuous Integration testing, several tools will be run to check your code for stylistic errors. Generating any warnings will cause the test to fail. Thus, good style is a requirement for submitting code to pandas.

Additionally, Continuous Integration will run code formatting checks like black, ruff, isort, and clang-format and more using pre-commit hooks. Any warnings from these checks will cause the Continuous Integration to fail; therefore, it is helpful to run the check yourself before submitting code. This can be done by installing pre-commit (which should already have happened if you followed the instructions in Setting up your development environment) and then running:

```
pre-commit install
```

from the root of the pandas repository. Now all of the styling checks will be run each time you commit changes without your needing to run each one manually. In addition, using pre-commit will also allow you to more easily remain up-to-date with our code checks as they change.

Note that if needed, you can skip these checks with git commit --no-verify.

If you don’t want to use pre-commit as part of your workflow, you can still use it to run its checks with one of the following:

```
pre-commit run --files <files you have modified>
pre-commit run --from-ref=upstream/main --to-ref=HEAD --all-files
```

without needing to have done pre-commit install beforehand.

Finally, we also have some slow pre-commit checks, which don’t run on each commit but which do run during continuous integration. You can trigger them manually with:

```
pre-commit run --hook-stage manual --all-files
```

## Type hints

kloppy strongly encourages the use of [PEP 484](https://peps.python.org/pep-0484/) style type hints. New development should contain type hints and pull requests to annotate existing code are accepted as well!

### Style guidelines

Type imports should follow the `from typing import ...` convention. Your code may be automatically re-written to use some modern constructs (e.g. using the built-in `list` instead of `typing.List`) by the pre-commit checks.

### Validating type hints

kloppy uses [pyright](https://github.com/microsoft/pyright) to statically analyze the codebase and type hints. After making any change you can ensure your type hints are consistent by running

```sh
uv run poe check
```

in your python environment.

## Test-driven development

kloppy is serious about testing and strongly encourages contributors to embrace [test-driven development (TDD)](https://en.wikipedia.org/wiki/Test-driven_development).

### Writing tests

All tests should go into the `kloppy/tests` subdirectory of the specific package. This folder contains many current examples of tests, and we suggest looking to these for inspiration.

### Running the test suite

The tests can then be run directly inside your Git clone (without having to install pandas) by typing:

```
pytest pandas
```

Often it is worth running only a subset of tests first around your changes before running the entire suite (tip: you can use the pandas-coverage app) to find out which tests hit the lines of code you’ve modified, and then run only those).

The easiest way to do this is with:

```
pytest pandas/path/to/test.py -k regex_matching_test_name
```

Or with one of the following constructs:

```
pytest pandas/tests/[test-module].py
pytest pandas/tests/[test-module].py::[TestClass]
pytest pandas/tests/[test-module].py::[TestClass]::[test_method]
```

## Testing with continuous integration

The kloppy test suite will run automatically on [GitHub Actions](https://github.com/features/actions/) continuous integration services, once your pull request is submitted. However, if you wish to run the test suite on a branch prior to submitting the pull request, then the continuous integration services need to be hooked to your GitHub repository. Instructions are [here](https://docs.github.com/en/actions/) for GitHub Actions. A pull-request will only be considered for merging when you have an all ‘green’ build.
