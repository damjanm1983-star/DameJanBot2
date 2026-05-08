# Binance Testnet Setup Guide

## What You Need to Provide

To connect DamJanBot to Binance Testnet, I need you to create API keys and share them with me.

---

## Step-by-Step: Get Your Testnet API Keys

### 1. Create a Binance Account (if you don't have one)
- Go to [Binance.com](https://www.binance.com)
- Sign up and complete verification

### 2. Access Testnet
- Go to [Binance Futures Testnet](https://testnet.binancefuture.com/)
- Log in with your Binance account

### 3. Generate API Keys
1. Click on **API Management** or **API Keys**
2. Click **Create API Key**
3. Give it a name (e.g., "DamJanBot-Testnet")
4. Complete any security verification (2FA, email, etc.)
5. **Copy and save both keys immediately**:
   - **API Key** (starts with letters/numbers)
   - **Secret Key** (longer string, only shown once!)

### 4. Important Security Notes
- ✅ These are TESTNET keys (fake money)
- ✅ Testnet is completely separate from your real Binance account
- ✅ You get free testnet funds to trade with
- ⚠️ Never share REAL (production) API keys
- ⚠️ The Secret Key is shown ONLY ONCE - save it immediately

---

## What to Send Me

Please provide:

```
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
```

I'll configure the bot with these credentials.

---

## After Setup

The bot will:
1. Connect to Binance Testnet
2. Show your testnet balance
3. Execute trades with fake money
4. Display real-time statistics on the dashboard

---

## Testnet Features

- **Free funds**: Binance gives you test USDT
- **Real market data**: Prices match real market
- **No risk**: All trades are simulated
- **Test strategies**: Perfect for testing your Heikin Ashi strategy

---

## Troubleshooting

### "Invalid API Key" Error
- Make sure you're using TESTNET keys, not production keys
- Regenerate keys if needed

### "Insufficient Balance" Error
- Testnet funds may need to be requested
- Go to Testnet dashboard and request test funds

### Connection Issues
- Testnet occasionally has maintenance
- Try again after a few minutes

---

## Next Steps After I Configure

1. I'll update the bot with your API keys
2. Restart the bot
3. Test with a manual webhook
4. Connect your TradingView alert
5. Monitor on dashboard: http://89.167.60.3:6000

---

**Ready? Send me your Testnet API Key and Secret Key!**
