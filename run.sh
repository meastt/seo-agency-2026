#!/bin/bash
# SEO Agency 2026 - Quick launcher
# Usage: ./run.sh

cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

# Run the CLI
./venv/bin/python -m workflows.cli
