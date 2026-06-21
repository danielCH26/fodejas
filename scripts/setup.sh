#!/bin/bash
set -e

echo "=== FODEJAS Setup Script ==="

if [ ! -f "pyproject.toml" ]; then
    echo "Error: pyproject.toml not found. Are you in the project root?"
    exit 1
fi

echo "Installing pre-commit..."
if command -v pip &> /dev/null; then
    pip install pre-commit
elif command -v pip3 &> /dev/null; then
    pip3 install pre-commit
else
    echo "Error: pip not found. Please install Python and pip first."
    exit 1
fi

echo "Installing pre-commit hooks..."
pre-commit install
pre-commit install --hook-type commit-msg

echo ""
echo "=== Setup Complete ==="
echo "Pre-commit hooks are now installed."
echo "Run 'pre-commit run --all-files' to test the hooks."
