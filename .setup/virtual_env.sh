#!/usr/bin/env bash
set -e

pip install uv
uv venv -p python3.11 venv
source venv/bin/activate
echo "Virtual environment 'venv' activated"
uv pip install -r ../requirements.txt
echo "Successfully installed requirements"