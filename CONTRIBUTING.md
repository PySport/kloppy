# Contributing to kloppy

When contributing to this repository, please discuss the change you wish to make with the repository owners
via [Issues](https://github.com/PySport/kloppy/issues) before making the change. This is to ensure that there
is nobody already working on the same issue and to ensure your time as a contributor isn't wasted!

## How to Contribute

All code changes happen through Pull Requests. If you would like to contribute, follow the steps below to set up
the project and make changes:

1. Fork the repo and create your branch from `master`.
1. Make code changes to fix a bug/add features
1. If you have added new code, add test(s) which cover the changes you have made. If you have updated existing code,
    verify that the existing tests cover the changes you have made and add/modify tests if needed.
1. Ensure that tests pass.
1. Ensure that your code conforms to the coding standard by either using the git hook (see instructions below) or by
    executing the command `black .` prior to committing your code.
1. Commit your code and create your Pull Request. Please specify in your Pull Request what change you have made and
    please specify if it relates to any existing issues.

## Project Setup

After you have forked the code and cloned it to your machine, execute the command `pip install -r requirements.txt`
in order to install all necessary project dependencies.

### Code Formatting

This project uses the _black_ code formatter to ensure all code conforms to a specified format. It is necessary to
format the code using _black_ prior to committing. There are two ways to do this, one is to manually run the command
`black .` (to run `black` on all `.py` files (or, `black <filename.py>` to run on a specific file).

Alternatively, it is possible to setup a Git hook to automatically run _black_ upon a `git commit` command. To do this,
follow these instructions:

- Execute the command `pre-commit install` to install the Git hook.
- When you next run a `git commit` command on the repository, _black_ will run and automatically format any changed
    files. _Note_: if _black_ needs to re-format a file, the commit will fail, meaning you will then need to execute
    `git add .` and `git commit` again to commit the files updated by _black_.
