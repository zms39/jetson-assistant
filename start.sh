#!/bin/bash
# Launcher for the Jetson assistant. Lives in the repo root.
# cd's to its own location so it works regardless of where it's called
# from or what the containing folder is named.
cd "$(dirname "$0")"
source venv/bin/activate
python main.py
