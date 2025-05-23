#!/bin/bash
set -e

# Set up local tools dir
mkdir -p .tools/bin
export PATH="$PWD/.tools/bin:$PATH"

# Install D2 (for diagrams)
if ! command -v d2 &>/dev/null; then
	curl -fsSL https://d2lang.com/install.sh | sh -s -- --prefix $PWD/.tools
fi

# Install uv
if ! command -v uv &>/dev/null; then
	curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="$PWD/.tools/bin" sh
fi

# Create and activate virtual environment
if [ ! -d ".venv" ]; then
	uv venv .venv
fi
source .venv/bin/activate

# Install package with docs dependencies
uv pip install ".[docs]"

# Build MkDocs site
mkdocs build -d site
