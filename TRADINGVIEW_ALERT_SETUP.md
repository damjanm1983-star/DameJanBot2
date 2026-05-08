# TradingView Alert Setup - Correct Configuration

## ⚠️ IMPORTANT: How the Bot Identifies Which Alert is Which

The bot needs to know WHICH bot (Bot1 or Bot2) sent the alert. Since TradingView doesn't automatically include the alert name in the webhook JSON, we need to add it manually.

---

## ✅ CORRECT Alert Message Format

### For DamjanBot1 (5min Chart)

**Alert Name:** `DamjanBot1`

**Message:**
```json
{"bot":"damjanbot1","action":"{{strategy.order.action}}","symbol":"{{ticker}}","price":{{close}}}
```

**Key difference:** Added `"bot":"damjanbot1"` at the beginning

---

### For DamjanBot2 (15min Chart)

**Alert Name:** `DamjanBot2`

**Message:**
```json
{"bot":"damjanbot2","event":"{{strategy.order.action}}","symbol":"{{ticker}}","price":{{close}},"time":"{{time}}","position":{{strategy.position_size}},"strategy":"v2w"}
```

**Key difference:** Added `"bot":"damjanbot2"` at the beginning

---

## 🔧 What Changed?

| Field | Purpose |
|-------|---------|
| `"bot":"damjanbot1"` | Tells the server this is from Bot1 |
| `"bot":"damjanbot2"` | Tells the server this is from Bot2 |

This field MUST be at the beginning of the JSON message.

---

## 📋 Full Setup Checklist

### Bot1 (5min)
- [ ] Alert Name: `DamjanBot1`
- [ ] Message: `{"bot":"damjanbot1","action":"{{strategy.order.action}}","symbol":"{{ticker}}","price":{{close}}}`
- [ ] Webhook URL: `http://89.167.60.3/webhook`
- [ ] Frequency: Once Per Bar Close

### Bot2 (15min)
- [ ] Alert Name: `DamjanBot2`
- [ ] Message: `{"bot":"damjanbot2","event":"{{strategy.order.action}}","symbol":"{{ticker}}","price":{{close}},"time":"{{time}}","position":{{strategy.position_size}},"strategy":"v2w"}`
- [ ] Webhook URL: `http://89.167.60.3/webhook`
- [ ] Frequency: Once Per Bar Close

---

## 🧪 Testing

Test Bot1:
```bash
curl -X POST http://89.167.60.3/webhook \
  -H "Content-Type: application/json" \
  -d '{"bot":"damjanbot1","action":"buy","symbol":"BTCUSDT","price":80000}'
```

Test Bot2:
```bash
curl -X POST http://89.167.60.3/webhook \
  -H "Content-Type: application/json" \
  -d '{"bot":"damjanbot2","event":"sell","symbol":"BTCUSDT","price":81000}'
```

---

## 📊 Dashboard URLs

- **Main**: http://89.167.60.3:8080
- **Bot1**: http://89.167.60.3:8080/damjanbot1
- **Bot2**: http://89.167.60.3:8080/damjanbot2

---

## ⚠️ Common Mistakes

1. **Forgetting the `bot` field** - The server won't know which bot sent the alert
2. **Wrong bot value** - Must be exactly `damjanbot1` or `damjanbot2`
3. **Typos** - JSON is case-sensitive

---

## 🔍 How Detection Works

The server checks in this order:
1. `bot_id` field
2. `bot` field (your setup)
3. `strategy` field
4. `message` field
5. Field structure (action vs event)

If nothing matches, it defaults to Bot1.
