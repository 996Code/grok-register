#!/bin/bash
set -e

# Start Xvfb for browser automation
echo "[web] Starting Xvfb..."
Xvfb :99 -screen 0 1280x900x24 -nolisten tcp &
sleep 1
export DISPLAY=:99

# Start Flask
echo "[web] Starting web server on :8080..."
cd /app/web
exec python3 app.py
