# Contributing to kloppy

When contributing to this repository, please discuss the change you wish to make with the repository owners 
via [Issues](https://github.com/PySport/kloppy/issues) before making the change. This is to ensure that there 
is nobody already working on the same issue and to ensure your time as a contributor isn't wasted!

## How to Contribute

All code changes happen through Pull Requests. If you would like to contribute, follow the steps below to set up 
the project and make changes:
1. Fork the repo and create your branch from `master`.
2. Make code changes to fix a bug/add features
3. If you have added new code, add test(s) which cover the changes you have made. If you have updated existing code, 
verify that the existing tests cover the changes you have made and add/modify tests if needed.
4. Ensure that tests pass.
5. Ensure that your code conforms to the coding standard by either using the git hook (see instructions below) or by 
executing the command `uv run pre-commit run -a` prior to committing your code.
6. Commit your code and create your Pull Request. Please specify in your Pull Request what change you have made and 
please specify if it relates to any existing issues.  

## Project Setup

After you have forked the code and cloned it to your machine, install
[uv](https://docs.astral.sh/uv/getting-started/installation/) and run the following
command from the repository directory to install the project dependencies, as in CI:

```shell
uv sync --frozen --all-extras
```

### Code Formatting

This project uses Ruff for formatting and linting, configured in
[`pyproject.toml`](pyproject.toml). Run the configured pre-commit checks manually with:

```shell
uv run pre-commit run -a
```

Alternatively, install the Git hooks to run the checks automatically when committing:

```shell
uv run pre-commit install
```

The hooks in [`.pre-commit-config.yaml`](.pre-commit-config.yaml) run Ruff and
synchronize dependencies, the lockfile, and exported requirements files. If a hook
modifies files, review and stage those changes, then retry the commit.
