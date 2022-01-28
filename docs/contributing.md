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
executing the command `black .` prior to committing your code. 
6. Commit your code and create your Pull Request. Please specify in your Pull Request what change you have made and 
please specify if it relates to any existing issues.  

## Project Setup

After you have forked the code and cloned it to your machine, execute the following commands in order to install all necessary
project dependencies. It is recommanded to create a virtual environment.

### Environment setup

```bash
# create virtual environment
python3 -m virtualenv .venv
source .venv/bin/activate

# bump dependencies inside virtual env
python -m pip install -U pip setuptools wheel
python -m pip install -e .

# install extra dependencies
python -m pip install -e '.[test]'
python -m pip install -e '.[development]'
python -m pip install -e '.[query]'
```

## Code Formatting

This project uses the _black_ code formatter to ensure all code conforms to a specified format. It is necessary to 
format the code using _black_ prior to committing. There are two ways to do this, one is to manually run the command
 `black .` (to run `black` on all `.py` files (or, `black <filename.py>` to run on a specific file).

Alternatively, it is possible to setup a Git hook to automatically run _black_ upon a `git commit` command. To do this,
follow these instructions:

- Execute the command `pre-commit install` to install the Git hook.
- When you next run a `git commit` command on the repository, _black_ will run and automatically format any changed
files. *Note*: if _black_ needs to re-format a file, the commit will fail, meaning you will then need to execute
`git add .` and `git commit` again to commit the files updated by _black_.

## Documentation

This project uses [MkDocs](https://www.mkdocs.org/) to generate documentation from pages written in Markdown.

To build docs :

```bash
# install dependencies for documentation (in virtual env)
python -m pip install -r docs-requirements.txt

# start MkDocs built-in dev-server
mkdocs serve
```

Open up [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser to preview your documentation.

## Contributors (sorted alphabetically)

Many thanks to the following developers for contributing to this project:

<style id="two-columns-ul">
style#two-columns-ul + ul {
  columns: 2
} 
</style>

- [Benjamin Larrousse](https://github.com/BenjaminLarrousse)
- [Benoît Blanc](https://github.com/benoitblanc)
- [Bruno Dagnino](https://github.com/bdagnino)
- [Cedric Krause](https://github.com/cedrickrause)
- [Daniel Mallory](https://github.com/dmallory42)
- [Daniel Z.](https://github.com/znstrider)
- [Eujern Lim](https://github.com/eujern)
- [Felix Schmidt](https://github.com/schmidtfx)
- [Ingmar van Dijk](https://github.com/ivd-git)
- [Jan van Haaren](https://github.com/JanVanHaaren)
- [Joe Mulberry](https://github.com/joemulberry)
- [Koen Vossen](https://github.com/koenvo)
- [Marcelo Trylesinski](https://github.com/Kludex)
- [Matias Bordese](https://github.com/matiasb)
- [Milan Klaasman](https://github.com/MKlaasman)
- [Pratik Thanki](https://github.com/pratikthanki)
- [Ricardo Tavares](https://github.com/rjtavares)
- [Thomas Seidl](https://github.com/ThomasSeidl)
- [Tim Keller](https://github.com/TK5-Tim)
- [Will McGugan](https://github.com/willmcgugan)
