#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m venv .venv-field
.venv-field/bin/python -m pip install 'numpy>=1.24,<3' 'Pillow>=10,<13'
