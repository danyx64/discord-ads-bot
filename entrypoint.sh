#!/bin/sh
set -eu
DATA_DIR="${DATA_DIR:-/data}"
mkdir -p "$DATA_DIR"
if [ ! -f "$DATA_DIR/config.json" ]; then cp /app/defaults/config.json "$DATA_DIR/config.json"; fi
if [ ! -f "$DATA_DIR/message.txt" ]; then cp /app/defaults/message.txt "$DATA_DIR/message.txt"; fi
exec python /app/bot.py
