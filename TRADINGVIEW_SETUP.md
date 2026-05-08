# TradingView Alert Setup for Multi-Bot

## Overview
You have 2 bots running on the same server:
- **DamjanBot1** → 5min timeframe → `/damjanbot1`
- **DamjanBot2** → 15min timeframe → `/damjanbot2`

Both use the SAME webhook URL but different messages to identify themselves.

---

## Webhook URL (Same for Both)
```
http://89.167.60.3/webhook
```

---

## Alert Message Format

### For DamjanBot1 (5min Chart)
```json
{"action":"{{strategy.order.action}}","symbol":"{{ticker}}","price":{{close}},"strategy":"v1"}
```

### For DamjanBot2 (15min Chart)
```json
{"event":"{{strategy.order.action}}","symbol":"{{ticker}}","price":{{close}},"strategy":"v2w"}
```

---

## Key Differences

| Field | DamjanBot1 | DamjanBot2 |
|-------|-----------|-----------|
| Action field | `"action"` | `"event"` |
| Strategy ID | `"v1"` | `"v2w"` |
| Timeframe | 5min | 15min |
| Dashboard | `/damjanbot1` | `/damjanbot2` |

---

## How It Works

The server detects which bot sent the alert by:
1. Checking `"strategy"` field (`v1` = Bot1, `v2w` = Bot2)
2. If no strategy field, checking if `"action"` exists (Bot1) or `"event"` exists (Bot2)

Each bot has:
- Separate state file
- Separate trade history
- Separate balance tracking
- Separate dashboard

---

## Dashboard URLs

| Bot | Dashboard URL | API Status |
|-----|--------------|------------|
| DamjanBot1 | http://89.167.60.3:8080/damjanbot1 | http://89.167.60.3:8080/damjanbot1/api/status |
| DamjanBot2 | http://89.167.60.3:8080/damjanbot2 | http://89.167.60.3:8080/damjanbot2/api/status |
| Main Page | http://89.167.60.3:8080 | - |

---

## Testing

Test Bot1:
```bash
curl -X POST http://89.167.60.3/webhook \
  -H "Content-Type: application/json" \
  -d '{"action":"buy","symbol":"BTCUSDT","price":80000,"strategy":"v1"}'
```

Test Bot2:
```bash
curl -X POST http://89.167.60.3/webhook \
  -H "Content-Type: application/json" \
  -d '{"event":"sell","symbol":"BTCUSDT","price":81000,"strategy":"v2w"}'
```

---

## Important Notes

1. **Same webhook URL** for both alerts
2. **Different `"strategy"` field** to identify which bot
3. Each bot tracks its own positions independently
4. No interference between bots
5. Both can be in different positions at the same time
