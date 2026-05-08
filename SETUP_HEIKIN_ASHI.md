# Heikin Ashi Strategy Setup Guide for Binance Testnet

This guide configures DamJanBot to work with your Heikin Ashi Pine Script strategy on **Binance Testnet**.

---

## 📋 What You Have

### Your Pine Script Strategy
- **Heikin Ashi Strategy V2 [Alorse]**
- Uses Heikin Ashi candles with EMA crossover
- Optional MACD filter
- Generates BUY/SELL signals

### DamJanBot
- Webhook receiver for TradingView alerts
- Dry-run/paper trading engine
- Dashboard for monitoring
- Binance Testnet integration

---

## 🚀 Setup Steps

### 1. Binance Testnet API Keys

1. Go to [Binance Testnet](https://testnet.binancefuture.com/)
2. Create an account or log in
3. Generate API Key and Secret
4. Save them securely

### 2. Configure Environment Variables

Create a `.env` file in the bot directory:

```bash
# Binance Testnet Credentials
export BINANCE_API_KEY="your_testnet_api_key"
export BINANCE_SECRET_KEY="your_testnet_secret_key"
export PAPER_MODE="true"

# Trading Settings
export SYMBOL="BTCUSDT"
export POSITION_ALLOCATION_PERCENT="0.25"
export TARGET_LEVERAGE="3"
export MAX_NOTIONAL_CAP_USDT="50000"

# Webhook
export WEBHOOK_PORT="8000"

# Optional: Telegram Notifications
export TELEGRAM_BOT_TOKEN=""
export TELEGRAM_CHAT_ID=""
```

Load the environment:
```bash
source .env
```

### 3. Update Pine Script for Webhook

Use the provided `BTCUSDT_HeikinAshi_Webhook.pine` file:

1. Open TradingView
2. Open Pine Editor
3. Paste the contents of `BTCUSDT_HeikinAshi_Webhook.pine`
4. Click "Add to Chart"

### 4. Create TradingView Alert

1. Click the **Alerts** button (clock icon)
2. Click **Create Alert**
3. Configure:
   - **Condition**: Select "Heikin Ashi Strategy V2 [Alorse] - Webhook"
   - **Message**: `{"action":"{{strategy.order.action}}","symbol":"{{ticker}}","price":{{close}}}`
   - **Frequency**: "Once Per Bar Close" ⭐ IMPORTANT!
   - **Webhook URL**: `http://89.167.60.3:8000/webhook`

### 5. Start the Bot

```bash
# Navigate to bot directory
cd /path/to/DamJanBot

# Activate virtual environment (if using)
source venv/bin/activate

# Start the webhook server
python3 trading_bot_server.py
```

The bot will:
- Start webhook server on port 8000
- Start dashboard on port 6000
- Connect to Binance Testnet
- Wait for TradingView alerts

---

## 📊 How It Works

### Signal Flow
```
TradingView (Pine Script)
    ↓
Alert Fires (BUY/SELL)
    ↓
Webhook → DamJanBot
    ↓
Process Signal
    ↓
Binance Testnet API (if not in paper mode)
    ↓
Update Dashboard
```

### Position Logic
- **BUY signal + FLAT** → Open LONG position
- **SELL signal + FLAT** → Open SHORT position
- **BUY signal + SHORT** → Flip to LONG (close SHORT, open LONG)
- **SELL signal + LONG** → Flip to SHORT (close LONG, open SHORT)
- **Same signal as current position** → Ignored (deduplication)

---

## 🧪 Testing

### Test Webhook Manually
```bash
curl -X POST http://89.167.60.3:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"action":"buy","symbol":"BTCUSDT","price":70000}'
```

### Check Bot Status
```bash
curl http://localhost:6000/api/status
```

### View Dashboard
Open `http://89.167.60.3:6000` in browser

---

## ⚙️ Configuration Options

### config.py Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PAPER_MODE` | true | If true, simulates trades without real execution |
| `SYMBOL` | BTCUSDT | Trading pair |
| `POSITION_ALLOCATION_PERCENT` | 0.25 | % of balance per trade (0.25 = 25%) |
| `TARGET_LEVERAGE` | 3 | Leverage multiplier |
| `MAX_NOTIONAL_CAP_USDT` | 50000 | Max position size in USDT |

### Pine Script Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `res` | 60 | Heikin Ashi timeframe (minutes) |
| `res1` | 180 | EMA timeframe |
| `fama` | 1 | Fast EMA period |
| `sloma` | 30 | Slow EMA period |
| `macdf` | false | Enable MACD filter |

---

## 🔒 Security Notes

- ✅ **Always use PAPER_MODE=true** for testing
- ✅ **Never commit API keys** to git
- ✅ **Use .env file** for secrets
- ✅ **Binance Testnet** uses fake money

---

## 🐛 Troubleshooting

### Webhook Not Receiving Alerts
1. Check firewall rules (port 8000 open)
2. Verify webhook URL in TradingView
3. Check bot logs: `tail -f /tmp/trading_bot.log`

### Duplicate Alerts
- Ensure "Once Per Bar Close" is selected
- Bot has 30-second deduplication window

### Binance API Errors
- Verify Testnet keys (not production keys)
- Check PAPER_MODE setting
- Ensure sufficient testnet balance

---

## 📈 Next Steps

1. **Monitor Performance** - Check dashboard regularly
2. **Adjust Strategy** - Fine-tune Pine Script inputs
3. **Risk Management** - Set stop losses in Binance
4. **Go Live** - Only after thorough testing (switch to production API keys)

---

## 📞 Support

- **Dashboard**: http://89.167.60.3:6000
- **API Status**: http://89.167.60.3:6000/api/status
- **Webhook**: http://89.167.60.3:8000/webhook

---

*Happy Trading! 📈🤖*
