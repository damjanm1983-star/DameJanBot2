# Telegram Bot Setup Guide

## Your Bot Token
```
8619307561:AAEuopebkFEKGeyv2wbjcyWCgY7ANTWJ27Y
```

⚠️ **Keep this token secret!** Anyone with this token can control your bot.

---

## How to Get Your Chat ID

### Method 1: Using the Bot (Easiest)

1. **Open Telegram** and search for your bot
   - Your bot username: `@DamJanBot` (or whatever you named it)
   - Or use this link: https://t.me/DamJanBot

2. **Send any message** to your bot (e.g., "Hello")

3. **Get your Chat ID** by visiting this URL in your browser:
   ```
   https://api.telegram.org/bot8619307561:AAEuopebkFEKGeyv2wbjcyWCgY7ANTWJ27Y/getUpdates
   ```

4. **Look for the "chat" section** in the response:
   ```json
   {
     "update_id": 123456789,
     "message": {
       "chat": {
         "id": 123456789,  <-- THIS IS YOUR CHAT ID
         "first_name": "Your Name",
         "type": "private"
       }
     }
   }
   ```

5. **Copy the Chat ID** (the number after `"id":`)

---

### Method 2: Using @userinfobot

1. In Telegram, search for: `@userinfobot`
2. Start the bot
3. It will reply with your user info including your ID
4. Your ID is the Chat ID

---

### Method 3: For Group/Channel

If you want notifications in a **group** or **channel**:

1. Add your bot to the group/channel
2. Send a message in the group
3. Use the same `getUpdates` URL above
4. Look for `"chat": {"id": -1001234567890}` (group IDs start with `-100`)

---

## What is Chat ID?

The Chat ID is a unique number that identifies:
- **Your personal account** (positive number, e.g., `123456789`)
- **A group** (negative number starting with `-`, e.g., `-1001234567890`)
- **A channel** (negative number starting with `-100`)

---

## Example

```
Chat ID: 123456789
```

Or for a group:
```
Chat ID: -1001234567890
```

---

## Next Steps

Once you have your Chat ID, send it to me and I'll configure the bot to send notifications for:
- 📈 Position opened
- 📉 Position closed
- 💰 Realized P&L
- 🔄 Position flipped

---

## Test Your Bot

After setup, you can test by sending:
```
https://api.telegram.org/bot8619307561:AAEuopebkFEKGeyv2wbjcyWCgY7ANTWJ27Y/sendMessage?chat_id=YOUR_CHAT_ID&text=Test%20message
```

Replace `YOUR_CHAT_ID` with your actual Chat ID.
