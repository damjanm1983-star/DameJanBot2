# Balance Calculation Logic

## How It Works

The bot **always uses 50% of the CURRENT balance** for each new position, including realized profits/losses from previous trades.

## Example Scenario

### Starting Point
- **Initial Balance**: $1,000.00

### Trade 1: First Order
- **Balance**: $1,000.00
- **50% of balance**: $500.00 (margin)
- **Position value**: $500 / 0.30 = $1,666.67
- **BTC size**: $1,666.67 / $80,000 = 0.020833 BTC

### Close Trade 1 with $20 Profit
- **Realized PnL**: +$20.00
- **Updated Balance**: $1,000 + $20 = **$1,020.00**

### Trade 2: Second Order
- **Balance**: $1,020.00 (includes previous profit)
- **50% of balance**: $510.00 (margin)
- **Position value**: $510 / 0.30 = $1,700.00
- **BTC size**: $1,700 / $81,000 = 0.020988 BTC

## Key Points

1. ✅ **Dynamic Balance**: Balance updates after each closed trade
2. ✅ **50% Allocation**: Always takes 50% of current balance
3. ✅ **30% Margin**: Uses 30% margin (~3.33x leverage)
4. ✅ **Compounding**: Profits increase position size, losses decrease it

## Formula

```
Margin Amount = Current Balance × 50%
Position Value = Margin Amount / 30%
BTC Size = Position Value / Current BTC Price
```

## Visual Example

```
Start:     $1,000 → Trade 1: $500 margin → $1,666 position
                    ↓
            Close with +$20 profit
                    ↓
Balance:   $1,020 → Trade 2: $510 margin → $1,700 position
                    ↓
            Close with -$10 loss
                    ↓
Balance:   $1,010 → Trade 3: $505 margin → $1,683 position
```

## Confirmation

This logic is implemented in the `_calculate_position_size()` method and `_flip_position()` method in `multi_bot_server.py`.
