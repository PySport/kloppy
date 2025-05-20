#!/bin/bash
set -e

# Install D2
curl -fsSL https://d2lang.com/install.sh | sh -s -- --prefix ./bin "$D2_VERSION"
export PATH="$PWD/bin:$PATH"

# Install kloppy and docs requirements
pip install .
pip install -r docs-requirements.txt

# Build MkDocs site
mkdocs build -d site
