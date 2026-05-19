#!/usr/bin/env bash
set -e
pip install -r requirements.txt
MODAL_TOKEN_ID=$MODAL_TOKEN_ID MODAL_TOKEN_SECRET=$MODAL_TOKEN_SECRET python3 -m modal deploy modal_app.py
