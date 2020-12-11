#!/usr/bin/env bash

rm -r build_venv
python3.8 -m venv build_venv
source ./build_venv/bin/activate
pip install --upgrade pip
pip install wheel
pip install -r requirements.txt --use-deprecated=legacy-resolver
pip install pyinstaller
