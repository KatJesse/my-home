#!/bin/sh
set -eu
export HAUS_DATA=/config
exec /opt/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8099 --proxy-headers
