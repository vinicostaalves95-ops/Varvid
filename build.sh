#!/usr/bin/env bash
set -e
pip install -r requirements.txt

# Cria config do Modal com o token
mkdir -p ~/.modal
cat > ~/.modal/credentials.toml << EOF
[default]
token_id = "${MODAL_TOKEN_ID}"
token_secret = "${MODAL_TOKEN_SECRET}"
EOF

python3 -m modal deploy modal_app.py
