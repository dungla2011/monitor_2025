#!/bin/bash

# Linux Deployment Script for Monitor Service Thread Pool Version
# This script helps configure Linux system for optimal monitor service performance

echo "🐧 Monitor Service - Linux Deployment Configuration"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check current system limits
print_info "Checking current system limits..."
echo "Current ulimit values:"
ulimit -a

echo ""
print_info "Key limits for monitoring service:"
echo "Max user processes: $(ulimit -u)"
echo "Open files: $(ulimit -n)"
echo "Stack size: $(ulimit -s) KB"

# Check if limits are sufficient
MAX_PROCESSES=$(ulimit -u)
OPEN_FILES=$(ulimit -n)

if [ "$MAX_PROCESSES" -lt 10000 ]; then
    print_warning "Max user processes ($MAX_PROCESSES) may be too low for large monitor counts"
    print_info "Recommended: At least 10,000 for 3000+ monitors"
fi

if [ "$OPEN_FILES" -lt 10000 ]; then
    print_warning "Open files limit ($OPEN_FILES) may be too low"
    print_info "Recommended: At least 10,000"
fi

echo ""
print_info "Thread Pool Architecture Benefits:"
echo "- Original: 3000 monitors = 3000+ threads ❌"
echo "- Thread Pool: 3000 monitors = 50 worker threads ✅"
echo "- Memory usage: Significantly reduced"
echo "- System load: Much lower"

# Check available memory
print_info "Checking system memory..."
free -h

# Check CPU info
print_info "Checking CPU information..."
echo "CPU cores: $(nproc)"
echo "CPU info: $(grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)"

# Recommend optimal configuration
echo ""
print_info "Recommended Configuration for your system:"

TOTAL_CORES=$(nproc)
RECOMMENDED_THREADS=$((TOTAL_CORES * 2))
if [ "$RECOMMENDED_THREADS" -gt 100 ]; then
    RECOMMENDED_THREADS=100
fi
if [ "$RECOMMENDED_THREADS" -lt 20 ]; then
    RECOMMENDED_THREADS=20
fi

echo "MAX_WORKER_THREADS=$RECOMMENDED_THREADS"
echo "MONITOR_QUEUE_SIZE=5000"
echo "TASK_TIMEOUT_SECONDS=180"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root. Consider creating a dedicated user for the monitor service."
fi

# Suggest deployment strategies
echo ""
print_info "Deployment Strategies for 3000+ Monitors:"
echo ""
echo "Strategy 1: Single Instance (if system has enough resources)"
echo "  python monitor_service_threadpool.py start"
echo "  - Uses $RECOMMENDED_THREADS worker threads"
echo "  - Handles all 3000 monitors"
echo "  - Requires robust system"
echo ""

echo "Strategy 2: Multiple Instances (Recommended for high load)"
echo "  Terminal 1: python monitor_service_threadpool.py start --chunk=1-1000"
echo "  Terminal 2: python monitor_service_threadpool.py start --chunk=2-1000"  
echo "  Terminal 3: python monitor_service_threadpool.py start --chunk=3-1000"
echo "  - Each instance uses $RECOMMENDED_THREADS worker threads"
echo "  - Total: 3000 monitors across 3 instances"
echo "  - Better resource distribution"
echo ""

echo "Strategy 3: Conservative Approach (for limited resources)"
echo "  Terminal 1: python monitor_service_threadpool.py start --chunk=1-500"
echo "  Terminal 2: python monitor_service_threadpool.py start --chunk=2-500"
echo "  Terminal 3: python monitor_service_threadpool.py start --chunk=3-500"
echo "  Terminal 4: python monitor_service_threadpool.py start --chunk=4-500"
echo "  Terminal 5: python monitor_service_threadpool.py start --chunk=5-500"
echo "  Terminal 6: python monitor_service_threadpool.py start --chunk=6-500"
echo "  - Each instance: 500 monitors with fewer threads"
echo "  - More instances, lower resource per instance"

# Check if systemd is available
if command -v systemctl >/dev/null 2>&1; then
    echo ""
    print_info "Systemd detected. You can create service files for auto-start:"
    echo "Example service file locations:"
    echo "  /etc/systemd/system/monitor-service-1.service"
    echo "  /etc/systemd/system/monitor-service-2.service"
    echo "  /etc/systemd/system/monitor-service-3.service"
fi

# Check Python virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    print_success "Virtual environment detected: $VIRTUAL_ENV"
else
    print_warning "No virtual environment detected. Consider using venv for better isolation."
fi

# Final recommendations
echo ""
print_info "Final Recommendations:"
echo "1. Use .env.linux for Linux-optimized settings"
echo "2. Start with Strategy 2 (3 instances of 1000 monitors each)"
echo "3. Monitor system resources during operation"
echo "4. Adjust MAX_WORKER_THREADS based on CPU usage"
echo "5. Use systemd service files for production deployment"

echo ""
print_success "Linux deployment analysis complete!"
print_info "Ready to start monitor service with: python monitor_service_threadpool.py start"