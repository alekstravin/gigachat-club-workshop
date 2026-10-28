#!/bin/sh
set -eu
TASK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$TASK_DIR"
if [ -x "$TASK_DIR/.venv/bin/python3" ]; then
    TASK_PYTHON="$TASK_DIR/.venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    TASK_PYTHON=$(command -v python3)
else
    echo 'Install Python 3.10+ first; see README-PORTABLE.md.'
    exit 1
fi
if ! "$TASK_PYTHON" -c 'import cryptography' >/dev/null 2>&1; then
    echo 'Dependency missing. Follow README-PORTABLE.md: create .venv and install requirements.txt first.'
    exit 1
fi
if [ ! -f generated/news-agent-personal.json ]; then
    echo 'Run setup_newsroom.py first and import generated/news-agent-personal.json; see README-PORTABLE.md.'
    exit 1
fi
echo 'Open http://127.0.0.1:8275 — stop with Ctrl+C.'
echo 'If the port is already occupied, stop here and check the existing collector. Do not terminate unrelated processes.'
exec "$TASK_PYTHON" server.py
