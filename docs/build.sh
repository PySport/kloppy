#!/bin/bash
set -e

# Install D2
curl -fsSL https://d2lang.com/install.sh | sh -s -- --prefix $PWD/deps/d2
export PATH="$PWD/deps/d2/bin:$PATH"

# Install kloppy and docs requirements
pip install .
pip install -r requirements-docs.txt

# Build MkDocs site
mkdocs build --strict -d site
