#!/bin/bash
set -e

# Build MkDocs site
pip install -r docs-requirements.txt
mkdocs build -d site
