# DamJanBot - Multi-Bot Trading System

**Automated Trading Bot for Binance Futures Testnet**

This system connects TradingView Pine Script strategies to Binance Futures Testnet via webhooks, supporting multiple bots with independent tracking.

---

## Features

- **Multi-Bot Support**: Run multiple strategies simultaneously (e.g., 5min + 15min)
- **Real-Time Dashboard**: Web-based monitoring on port 8080
- **Telegram Notifications**: Instant trade alerts
- **Dynamic Position Sizing**: 50% of current balance with 30% margin
- **Live P&L Tracking**: Real-time profit/loss calculation
- **Auto-Start on Boot**: Systemd service for reliability
- **Fail2Ban Protection**: Webhook security against abuse

---

## Architecture

```
TradingView (Pine Script)
    ↓ Webhook Alert
DamJanBot Server (Port 80/8080)
    ↓ Process Signal
Binance Testnet API (Price Data)
    ↓ Update
Dashboard + Telegram
```

---

## Quick Start

### 1. TradingView Alert Setup

**DamjanBot1 (5min timeframe):**
```json
{"bot":"damjanbot1","action":"{{strategy.order.action}}","symbol":"{{ticker}}","price":{{close}}}
```

**DamjanBot2 (15min timeframe):**
```json
{"bot":"damjanbot2","event":"{{strategy.order.action}}","symbol":"{{ticker}}","price":{{close}},"time":"{{time}}","position":{{strategy.position_size}},"strategy":"v2w"}
```

**Webhook URL:** `http://89.167.60.3/webhook`

### 2. Dashboard URLs

| Dashboard | URL |
|-----------|-----|
| Main | http://89.167.60.3:8080 |
| Bot1 (5min) | http://89.167.60.3:8080/damjanbot1 |
| Bot2 (15min) | http://89.167.60.3:8080/damjanbot2 |

### 3. API Status Endpoints

- Bot1: `http://89.167.60.3:8080/damjanbot1/api/status`
- Bot2: `http://89.167.60.3:8080/damjanbot2/api/status`

---

## Configuration

### Environment Variables (.env file)

```bash
# Binance Testnet API Keys
export BINANCE_API_KEY="your_api_key"
export BINANCE_SECRET_KEY="your_secret_key"

# Trading Settings
export PAPER_MODE="true"
export SYMBOL="BTCUSDT"
export POSITION_ALLOCATION_PERCENT="0.50"
export MARGIN_PERCENT="0.30"

# Webhook
export WEBHOOK_PORT="80"

# Telegram Notifications
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### Trading Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Initial Balance | $1,000.00 | Starting balance per bot |
| Position Size | 50% | Of current balance |
| Margin | 30% | ~3.33x leverage |
| Mode | DRY-RUN | Paper trading (no real money) |

---

## Balance Calculation Logic

The bot uses **dynamic balance calculation**:

1. **First Order**: 50% of $1,000 = $500 margin → $1,666.67 position
2. **Close with +$20 profit**: Balance = $1,020
3. **Second Order**: 50% of $1,020 = $510 margin → $1,700 position
4. **Close with -$10 loss**: Balance = $1,010
5. **Third Order**: 50% of $1,010 = $505 margin → $1,683.33 position

**Formula:**
```
Margin Amount = Current Balance × 50%
Position Value = Margin Amount ÷ 30%
BTC Size = Position Value ÷ Current Price
```

---

## System Services

### DamJanBot Service

```bash
# Check status
sudo systemctl status damjanbot

# Start/Stop/Restart
sudo systemctl start damjanbot
sudo systemctl stop damjanbot
sudo systemctl restart damjanbot

# View logs
sudo tail -f /var/log/damjanbot.log
```

### Fail2Ban Protection

```bash
# Check status
sudo fail2ban-client status

# View banned IPs
sudo fail2ban-client status damjanbot-webhook

# Unban IP
sudo fail2ban-client set damjanbot-webhook unbanip <IP>
```

---

## File Structure

```
DamJanBot/
├── multi_bot_server.py      # Main server (webhook + dashboard)
├── config.py                # Configuration class
├── dry_run_engine.py        # Trading simulation engine
├── binance_api_client.py    # Binance API wrapper
├── telegram_notifier.py     # Telegram notifications
├── .env                     # Environment variables
├── .env.example             # Example configuration
├── bot_state_*.json         # Bot state files (auto-generated)
├── alert_log_*.jsonl        # Alert logs (auto-generated)
├── get_chat_id.py           # Telegram Chat ID helper
├── SETUP_HEIKIN_ASHI.md     # Heikin Ashi setup guide
├── TRADINGVIEW_ALERT_SETUP.md  # Alert configuration
├── TELEGRAM_SETUP.md        # Telegram setup guide
├── BALANCE_LOGIC.md         # Balance calculation docs
└── README.md                # This file
```

---

## Security

- **Fail2Ban**: Protects against webhook abuse
- **Dry-Run Mode**: No real money at risk
- **Testnet Only**: Uses Binance test environment
- **IP Whitelist**: Only accepts webhooks (configure as needed)

---

## Troubleshooting

### Bot Not Responding
```bash
# Check if service is running
sudo systemctl status damjanbot

# Check logs
sudo tail -f /var/log/damjanbot.log

# Restart service
sudo systemctl restart damjanbot
```

### Dashboard Not Loading
- Ensure port 8080 is open in firewall
- Check if service is running: `curl http://89.167.60.3:8080`

### Telegram Not Working
- Verify bot token and chat ID in `.env`
- Test with: `python3 get_chat_id.py`
- Check bot is added to channel with admin rights

---

## Support

- **Dashboard**: http://89.167.60.3:8080
- **Webhook**: http://89.167.60.3/webhook
- **Logs**: `/var/log/damjanbot.log`

---

## License

Private - For personal use only.

---

**Created by:** Dame & Jan | 2026
