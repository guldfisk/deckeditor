#!/usr/bin/env bash

source build_venv/bin/activate
build_venv/bin/pyinstaller editor.spec --noconfirm
