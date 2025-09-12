#!/bin/bash
# File: kill_by_name.sh

if [ -z "$1" ]; then
    echo "Usage: $0 <process_name>"
    exit 1
fi

PROC_NAME=$1

# Tìm PID, loại bỏ dòng grep chính nó
PIDS=$(ps -ef | grep "$PROC_NAME" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "Không tìm thấy process với tên: $PROC_NAME"
    exit 0
fi

for PID in $PIDS; do
    echo "Killing PID: $PID ($PROC_NAME)"
    kill -9 $PID
done
