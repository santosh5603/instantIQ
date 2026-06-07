#!/bin/bash
# Start virtual display
Xvfb :99 -screen 0 1280x1024x24 &
export DISPLAY=:99

# Start the worker command
exec "$@"
