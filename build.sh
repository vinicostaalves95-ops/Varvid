#!/usr/bin/env bash
set -e

# Install Python dependencies
pip install -r requirements.txt

# Install FFmpeg
apt-get update -qq && apt-get install -y -qq ffmpeg
