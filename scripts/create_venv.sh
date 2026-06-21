#!/bin/bash
set -e

VENV_DIR=".venv"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_DIR"

if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at $VENV_DIR"
else
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Installing project with development dependencies..."
pip install -e ".[dev]"

echo "Done! Activate the virtual environment with: source $VENV_DIR/bin/activate"
