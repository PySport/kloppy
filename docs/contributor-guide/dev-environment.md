# Creating a development environment

To test out code changes, you'll need to set up a Python environment with all
required dependencies. It’s also highly recommended to install pre-commit
hooks to catch formatting issues early.

## Create an isolated Python environment

Before we begin, please:

- Make sure that you have cloned the repository
- `cd` to the kloppy source directory you just created with the clone command

### Option 1: using uv (recommended)

Kloppy uses [uv](https://docs.astral.sh/uv/) to manage dependencies. On macOS
and Linux, you can use `curl` to the download the installation script and
execute it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Information about installation options and instruction for Windows can be
found in [uv's installation guide](https://docs.astral.sh/uv/getting-started/installation/).

Next, create and activate a virtual environment using uv with a Python version
that kloppy supports:

```bash
uv venv --python 3.8
source .venv/bin/activate
```

!!! tip

    Currently, kloppy supports Python 3.8 through 3.12. However, we recommend
    using Python 3.8 to avoid relying on language features introduced in later
    versions.

Finally, run `uv sync` at the root of the repository. This sets up a full
development environment with all required dependencies.

```bash
uv sync
```

### Option 2: using pip

You'll need to have at least the minimum Python version that kloppy supports.

#### Unix/macOS with virtualenv

```bash
# Create a virtual environment
# Use an ENV_DIR of your choice. We'll use .venv
# Any parent directories should already exist
python3 -m venv .venv

# Activate the virtualenv
source .venv/bin/activate

# Install the build dependencies
python -m pip install -r requirements-dev.txt
```

#### Windows

Below is a brief overview on how to set up a virtual environment with
Powershell under Windows. For details please refer to the [official virtualenv
user guide](https://virtualenv.pypa.io/en/latest/user_guide.html#activators).

Use an `ENV_DIR` of your choice. We’ll use `~\\virtualenvs\\kloppy-dev` where
`~` is the folder pointed to by either `$env:USERPROFILE` (Powershell) or
`%USERPROFILE%` (cmd.exe) environment variable. Any parent directories should
already exist.

```bash
# Create a virtual environment
python -m venv $env:USERPROFILE\virtualenvs\pandas-dev

# Activate the virtualenv. Use activate.bat for cmd.exe
~\virtualenvs\pandas-dev\Scripts\Activate.ps1

# Install the build dependencies
python -m pip install -r requirements-dev.txt
```

## Install pre-commit hooks

Additionally, Continuous Integration will run code formatting checks like
`ruff` using [pre-commit hooks](https://pre-commit.com/). Any warnings from
these checks will cause the Continuous Integration to fail; therefore, it is
helpful to run the check yourself before submitting code. This can be done by
installing `pre-commit` (which should already have happened if you followed
the instructions above) and then running:

```bash
pre-commit install
```

Now all the styling checks will be run each time you commit changes without
you needing to run each one manually. In addition, using pre-commit will also
allow you to more easily remain up-to-date with our code checks as they
change.

Note that if needed, you can skip these checks with `git commit --no-verify`.

If you don’t want to use pre-commit as part of your workflow, you can still
use it to run its checks with one of the following:

```bash
pre-commit run --files <files you have modified>
pre-commit run --from-ref=upstream/main --to-ref=HEAD --all-files
```

## Updating the development environment

It is important to periodically update your local master branch with updates
from the kloppy master branch and update your development environment to
reflect any changes to the various packages that are used during development.

If using `uv`, run:

```bash
git checkout master
git fetch upstream
git merge upstream/master
uv sync
```

If using `pip`, do:

```bash
git checkout master
git fetch upstream
git merge upstream/master
# activate the virtual environment based on your platform
python -m pip install --upgrade -r requirements-dev.txt
```
