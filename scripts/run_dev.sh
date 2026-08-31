#!/usr/bin/env bash
# Startet die App direkt aus dem Quellcode (Linux/macOS, für Entwicklung).
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d .venv ]; then
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi
PYTHONPATH="$PWD/src" .venv/bin/python -m vinted_tool "$@"
