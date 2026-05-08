#!/bin/bash
# Test script for DamJanBot webhook

echo "=== DamJanBot Webhook Test ==="
echo "Server: 89.167.60.3"
echo ""

# Test BUY signal
echo "1. Testing BUY signal..."
curl -s -X POST http://89.167.60.3:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"action":"buy","symbol":"BTCUSDT","price":70000}' | python3 -m json.tool
echo ""

sleep 2

# Test SELL signal  
echo "2. Testing SELL signal..."
curl -s -X POST http://89.167.60.3:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"action":"sell","symbol":"BTCUSDT","price":72000}' | python3 -m json.tool
echo ""

sleep 1

# Check status
echo "3. Checking bot status..."
curl -s http://89.167.60.3:6000/api/status | python3 -m json.tool
echo ""

echo "=== Test Complete ==="
