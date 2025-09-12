#!/bin/bash

# Thread Count Monitor Script
# Usage: ./02-count_thread_by_process_name.sh <process_name>

# Kiểm tra input parameter
if [ $# -eq 0 ]; then
    echo "Usage: $0 <process_name>"
    echo "Example: $0 monitor_service"
    exit 1
fi

PROCESS_NAME="$1"
LOG_FILE="thread_count_${PROCESS_NAME}.log"

echo "Monitoring threads for: $PROCESS_NAME"
echo "Press Ctrl+C to stop"

# Trap để handle Ctrl+C
trap 'echo "Stopped"; exit 0' INT

# Main monitoring loop
while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    THREAD_COUNT=$(ps -efT | grep "$PROCESS_NAME" | grep -v grep | wc -l)
    echo "$TIMESTAMP | $THREAD_COUNT" | tee -a "$LOG_FILE"
    sleep 2
done
