#!/bin/bash
# Setup script for Binance Testnet API keys

echo "=========================================="
echo "DamJanBot - Binance Testnet Setup"
echo "=========================================="
echo ""
echo "This script will help you configure your Binance Testnet API keys"
echo ""

# Check if .env exists
if [ -f .env ]; then
    echo "Found existing .env file"
    echo "Current settings:"
    grep -E "(BINANCE|PAPER)" .env | grep -v "^#"
    echo ""
    read -p "Do you want to update the API keys? (y/n): " update
    if [ "$update" != "y" ]; then
        echo "Keeping existing configuration"
        exit 0
    fi
fi

echo ""
echo "Please enter your Binance Testnet API credentials:"
echo "(Get them from https://testnet.binancefuture.com/)"
echo ""

read -p "API Key: " api_key
read -p "Secret Key: " secret_key

echo ""
echo "Configuration:"
echo "API Key: ${api_key:0:10}..."
echo "Secret Key: ${secret_key:0:10}..."
echo ""

read -p "Is this correct? (y/n): " confirm

if [ "$confirm" = "y" ]; then
    cat > .env << EOF
# DamJanBot Configuration
export BINANCE_API_KEY="$api_key"
export BINANCE_SECRET_KEY="$secret_key"
export PAPER_MODE="true"
export SYMBOL="BTCUSDT"
export POSITION_ALLOCATION_PERCENT="0.50"
export MARGIN_PERCENT="0.30"
export WEBHOOK_PORT="80"
EOF
    echo ""
    echo "✅ Configuration saved to .env"
    echo ""
    echo "To activate: source .env"
    echo "To start bot: python3 trading_bot_server.py"
else
    echo "Cancelled. No changes made."
fi
