#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "[soulsense] Creating virtual environment..."
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi

source .venv/bin/activate

if [ "$1" = "--replay" ]; then
  python soulsense.py --replay captures/example_csi.csv
else
  python soulsense.py "$@"
fi
