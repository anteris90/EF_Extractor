#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
START_SCRIPT="$SCRIPT_DIR/Start Browser.sh"

if [ ! -f "$START_SCRIPT" ]; then
    echo "ERROR: Start script not found at $START_SCRIPT"
    echo
    read -r -p "Press Enter to close this window..." _
    exit 1
fi

bash "$START_SCRIPT" "$@"
STATUS=$?

echo
if [ $STATUS -ne 0 ]; then
    echo "Browser app exited with status $STATUS"
else
    echo "Browser app stopped"
fi

read -r -p "Press Enter to close this window..." _
exit $STATUS
