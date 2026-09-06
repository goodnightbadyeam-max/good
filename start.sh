#!/bin/bash
# LZMarket Bot - Linux Startup Script

echo "=========================================="
echo "       LZMarket Telegram Bot"
echo "=========================================="
echo ""
echo "[$(date)] Starting bot..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found!"
    exit 1
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "[ERROR] app.py not found!"
    exit 1
fi

# Start the bot
echo "[INFO] Bot is starting..."
echo "[INFO] Press Ctrl+C to stop"
echo "=========================================="
echo ""

python3 app.py

# If bot crashes
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo ""
    echo "=========================================="
    echo "[ERROR] Bot crashed with exit code: $exit_code"
    echo "=========================================="
fi

exit $exit_code
