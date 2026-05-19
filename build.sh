#!/usr/bin/env bash
set -e
pip install -r requirements.txt
python3 -m modal deploy modal_app.py
