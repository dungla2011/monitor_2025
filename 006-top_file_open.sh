#!/bin/sh

# Temporary files để lưu kết quả
TEMP_FILE="/tmp/top_file_open_$$"
RESULT_FILE="/tmp/top_file_open_result_$$"

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up temporary files..."
    rm -f "$TEMP_FILE" "$RESULT_FILE" 2>/dev/null
    exit 0
}

# Trap signals để cleanup khi thoát
trap cleanup INT TERM EXIT

echo "🚀 Starting TOP file open monitor..."
echo "📁 Temp files: $TEMP_FILE, $RESULT_FILE"
echo "   Press Ctrl+C to stop and cleanup"
echo ""

# First run - no clear needed
FIRST_RUN=true

while true; do
    # Tìm kết quả mới trước (không hiển thị gì)
    echo "🔄 Scanning processes..." >&2
    
    # Lưu kết quả vào temp file
    find /proc -maxdepth 2 -name fd -type d 2>/dev/null > "$TEMP_FILE"
    
    # Process temp file và lưu kết quả mới
    NEW_RESULT_FILE="${RESULT_FILE}.new"
    while read fd_dir; do
        pid=$(echo "$fd_dir" | cut -d'/' -f3)
        count=$(ls -1 "$fd_dir" 2>/dev/null | wc -l)
        if [ $count -gt 0 ]; then
            cmd=$(cat "/proc/$pid/comm" 2>/dev/null || echo "unknown")
            echo "$pid\t$count\t$cmd"
        fi
    done < "$TEMP_FILE" | sort -k2 -nr | head -20 > "$NEW_RESULT_FILE"
    
    # Khi đã có kết quả mới, clear màn hình (trừ lần đầu)
    if [ "$FIRST_RUN" = false ]; then
        clear
    fi
    FIRST_RUN=false
    
    # Hiển thị kết quả mới
    echo "=== TOP PIDs BY OPEN FILES COUNT (ULTRA FAST) ==="
    echo "$(date)"
    echo ""
    echo "PID\tFILE_COUNT\tCOMMAND"
    echo "---\t----------\t-------"
    
    cat "$NEW_RESULT_FILE"
    
    # Move new result to current result
    mv "$NEW_RESULT_FILE" "$RESULT_FILE"
    
    echo ""
    echo "📊 Results saved to: $RESULT_FILE"
    echo "🔄 Scanning for next update... (Press Ctrl+C to exit)"
    
    # Small delay before next scan
    sleep 1
done