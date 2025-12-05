#!/bin/bash
export NO_AT_BRIDGE=1
export GTK_A11Y=none
export PYTHONPATH=/app/lib/python3.12/site-packages:$PYTHONPATH

cd /app/lib/python3.12/site-packages
exec python3 -u main.py "$@"
