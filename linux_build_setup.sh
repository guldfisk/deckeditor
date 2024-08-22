#!/usr/bin/env bash

rm -r build_venv
python3.9 -m venv build_venv
source ./build_venv/bin/activate
poetry install
pip install pyinstaller
