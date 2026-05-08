# Clean Repository Structure

## Essential Files (Keep These)

### Core Application
- `multi_bot_server.py` - Main trading server (webhook + dashboard)
- `config.py` - Configuration management
- `dry_run_engine.py` - Paper trading engine
- `binance_api_client.py` - Binance API client
- `telegram_notifier.py` - Telegram notifications
- `position_reader.py` - Position state reader

### Configuration
- `.env.example` - Example environment variables
- `.gitignore` - Git ignore rules
- `requirements.txt` - Python dependencies

### Documentation
- `README.md` - Main documentation
- `SETUP_HEIKIN_ASHI.md` - Heikin Ashi setup
- `TRADINGVIEW_ALERT_SETUP.md` - TradingView alerts
- `TRADINGVIEW_SETUP.md` - TradingView configuration
- `TELEGRAM_SETUP.md` - Telegram setup
- `BALANCE_LOGIC.md` - Balance calculation docs
- `BINANCE_TESTNET_SETUP.md` - Testnet setup
- `ALERT_SETUP_GUIDE.md` - Alert setup guide

### Scripts
- `get_chat_id.py` - Telegram Chat ID helper
- `setup_testnet.sh` - Testnet setup script
- `test_webhook.sh` - Webhook test script

### Pine Scripts
- `BTCUSDT_HeikinAshi_Webhook.pine` - Heikin Ashi strategy
- `BTCUSDT_Clean_Single_Alert.pine` - Clean alert strategy
- `BTCUSDT_V7_5_webhook.pine` - V7.5 strategy

## Files Removed (Auto-generated/Old)
- State files (`bot_state_*.json`)
- Log files (`alert_log_*.jsonl`)
- Backup files
- Cache files (`__pycache__`, `*.pyc`)
- Old dashboard files
- Test HTML files
