# Git Push Instructions

## Current Status
- All changes are committed locally (11 commits ahead)
- Need to push to: https://github.com/damjanm1983-star/DameJanBot2

## How to Push

### Option 1: Using Personal Access Token (Recommended)

1. Generate a GitHub Personal Access Token:
   - Go to https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scopes: `repo` (full control of private repositories)
   - Generate and copy the token

2. Push using the token:
   ```bash
   cd /root/.openclaw/workspace/DamJanBot
   git push https://YOUR_USERNAME:YOUR_TOKEN@github.com/damjanm1983-star/DameJanBot2.git main
   ```

### Option 2: Using SSH Key

If you have SSH keys set up:
```bash
git remote set-url origin git@github.com:damjanm1983-star/DameJanBot2.git
git push origin main
```

### Option 3: Manual Push from Your Local Machine

1. Clone the repository on your local machine:
   ```bash
   git clone https://github.com/damjanm1983-star/DamJanBot.git
   cd DamJanBot
   ```

2. Add the new remote:
   ```bash
   git remote add newrepo https://github.com/damjanm1983-star/DameJanBot2.git
   ```

3. Fetch and push:
   ```bash
   git fetch origin
   git push newrepo main
   ```

## Files to Keep

These are the essential files for the bot:
```
multi_bot_server.py          # Main server
config.py                     # Configuration
dry_run_engine.py             # Trading engine
binance_api_client.py         # Binance API
telegram_notifier.py          # Telegram notifications
.env.example                  # Example config
README.md                     # Documentation
SETUP_HEIKIN_ASHI.md         # Setup guide
TRADINGVIEW_ALERT_SETUP.md   # Alert setup
TELEGRAM_SETUP.md            # Telegram setup
BALANCE_LOGIC.md             # Balance docs
get_chat_id.py               # Helper script
requirements.txt             # Python dependencies
```

## Files to Remove (Not Needed)

```
*.json                       # State files (auto-generated)
*.jsonl                      # Log files (auto-generated)
__pycache__/                 # Python cache
*.pyc                        # Compiled Python
.venv/                       # Virtual environment
venv/                        # Virtual environment
```

## Commands to Clean Up

```bash
cd /root/.openclaw/workspace/DamJanBot

# Remove auto-generated files
rm -f bot_state_*.json alert_log_*.jsonl
rm -rf __pycache__ *.pyc

# Create .gitignore
cat > .gitignore << 'EOF'
# State files
bot_state_*.json
alert_log_*.jsonl

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.env

# Logs
*.log
EOF

git add .gitignore
git commit -m "Add .gitignore for auto-generated files"
```
