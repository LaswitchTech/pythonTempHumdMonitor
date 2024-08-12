#!/bin/bash
source .env/bin/activate
python3 monitor.py "$@"
deactivate
