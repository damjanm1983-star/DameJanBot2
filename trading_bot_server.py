#!/usr/bin/env python3
"""
Trading Bot Server with Dry-Run Engine and Dashboard
- Receives TradingView webhooks
- Simulates trades with dry-run engine
- Serves monitoring dashboard on port 6000
- State persistence to survive restarts
- Alert deduplication to prevent double-processing
"""

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from dry_run_engine import DryRunEngine, OrderSide, OrderType
from telegram_notifier import TelegramNotifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("TradingBot")

# Constants
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot_state.json')
ALERT_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'alert_log.jsonl')
ALERT_DEDUP_WINDOW_SECONDS = 30  # Ignore duplicate alerts within 30 seconds


class PositionState:
    """Persistent position state management"""
    
    def __init__(self):
        self.symbol: str = "BTCUSDT"
        self.side: str = "FLAT"  # LONG, SHORT, or FLAT
        self.size: Decimal = Decimal("0")
        self.entry_price: Optional[Decimal] = None
        self.realized_pnl: Decimal = Decimal("0")
        self.trades_count: int = 0
        self.last_trade_time: Optional[str] = None
        self.last_alert_hash: Optional[str] = None
        self.last_alert_time: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "size": str(self.size),
            "entry_price": str(self.entry_price) if self.entry_price else None,
            "realized_pnl": str(self.realized_pnl),
            "trades_count": self.trades_count,
            "last_trade_time": self.last_trade_time,
            "last_alert_hash": self.last_alert_hash,
            "last_alert_time": self.last_alert_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PositionState':
        state = cls()
        state.symbol = data.get("symbol", "BTCUSDT")
        state.side = data.get("side", "FLAT")
        state.size = Decimal(str(data.get("size", "0")))
        state.entry_price = Decimal(str(data["entry_price"])) if data.get("entry_price") else None
        state.realized_pnl = Decimal(str(data.get("realized_pnl", "0")))
        state.trades_count = data.get("trades_count", 0)
        state.last_trade_time = data.get("last_trade_time")
        state.last_alert_hash = data.get("last_alert_hash")
        state.last_alert_time = data.get("last_alert_time")
        return state


class TradingBot:
    def __init__(self):
        # Setup environment for config
        os.environ['BINANCE_API_KEY'] = 'dry_run_key'
        os.environ['BINANCE_SECRET_KEY'] = 'dry_run_secret'
        os.environ['PAPER_MODE'] = 'true'
        
        self.config = Config()
        self.engine = DryRunEngine(self.config)
        
        # Initialize Telegram notifier
        self.telegram = TelegramNotifier(
            bot_token=self.config.telegram_bot_token,
            chat_id=self.config.telegram_chat_id
        )
        
        # Load persisted state
        self.position_state = self._load_state()
        
        # Sync engine with loaded state
        self._sync_engine_with_state()
        
        # Alert deduplication tracking
        self.recent_alerts: Dict[str, datetime] = {}  # hash -> timestamp
        
        logger.info("=" * 60)
        logger.info("🤖 Trading Bot initialized in DRY-RUN mode")
        logger.info(f"📊 Starting balance: $10,000.00")
        logger.info(f"📈 Position sizing: 50% of balance, 30% margin (~3.3x leverage)")
        logger.info(f"💾 State file: {STATE_FILE}")
        logger.info(f"🔄 Current position: {self.position_state.side} {self.position_state.size} BTC")
        if self.position_state.entry_price:
            logger.info(f"💰 Entry price: ${self.position_state.entry_price:,.2f}")
        if self.telegram.enabled:
            logger.info("📱 Telegram notifications: ENABLED")
        else:
            logger.info("📱 Telegram notifications: DISABLED")
        logger.info("=" * 60)
    
    def _load_state(self) -> PositionState:
        """Load position state from disk"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                state = PositionState.from_dict(data)
                logger.info(f"📂 Loaded state from {STATE_FILE}")
                return state
            except Exception as e:
                logger.warning(f"⚠️  Could not load state: {e}, starting fresh")
        return PositionState()
    
    def _save_state(self):
        """Save position state to disk"""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.position_state.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"❌ Could not save state: {e}")
    
    def _log_alert(self, alert_data: Dict[str, Any], result: Dict[str, Any], raw_body: str):
        """Log every alert received for debugging"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "raw_body": raw_body[:500],
                "parsed_alert": alert_data,
                "result": result,
                "position_before": self.position_state.side
            }
            with open(ALERT_LOG_FILE, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.warning(f"Could not log alert: {e}")
    
    def _sync_engine_with_state(self):
        """Sync the dry-run engine with our persisted state"""
        if self.position_state.side != "FLAT" and self.position_state.size > 0:
            # Create position in engine
            from dry_run_engine import SimulatedPosition, PositionSide
            pos = SimulatedPosition(
                symbol=self.position_state.symbol,
                side=PositionSide(self.position_state.side) if self.position_state.side in ["LONG", "SHORT"] else None,
                size=self.position_state.size,
                entry_price=self.position_state.entry_price,
                realized_pnl=self.position_state.realized_pnl
            )
            self.engine.positions[self.position_state.symbol] = pos
    
    def _get_alert_hash(self, alert_data: Dict[str, Any]) -> str:
        """Generate a hash for alert deduplication"""
        # Hash based on action, symbol, and price (rounded to reduce noise)
        action = alert_data.get('action', alert_data.get('event', '')).lower()
        symbol = alert_data.get('symbol', '')
        price = alert_data.get('price', 0)
        # Round price to nearest dollar for dedup purposes
        price_rounded = round(float(price)) if price else 0
        return f"{action}:{symbol}:{price_rounded}"
    
    def _is_duplicate_alert(self, alert_hash: str) -> bool:
        """Check if this is a duplicate alert within the dedup window"""
        now = datetime.now()
        
        # Clean up old entries
        cutoff = now - timedelta(seconds=ALERT_DEDUP_WINDOW_SECONDS)
        self.recent_alerts = {
            h: t for h, t in self.recent_alerts.items() if t > cutoff
        }
        
        # Check if we've seen this alert recently
        if alert_hash in self.recent_alerts:
            age = (now - self.recent_alerts[alert_hash]).total_seconds()
            logger.warning(f"⚠️  DUPLICATE ALERT detected (seen {age:.1f}s ago): {alert_hash}")
            return True
        
        # Record this alert
        self.recent_alerts[alert_hash] = now
        return False
    
    def _calculate_position_size(self, price: Decimal) -> Decimal:
        """Calculate position size based on config - 50% of balance with 30% margin"""
        # Get current balance (starts at 1000, updates with realized PnL)
        balance = self.engine.simulated_balance
        allocation = Decimal("0.50")  # 50% of balance
        margin = Decimal("0.30")      # 30% margin
        
        # Calculate position value with leverage from margin
        # 30% margin = ~3.33x leverage
        leverage = Decimal("1") / margin  # 3.33x
        position_value = balance * allocation * leverage
        quantity = position_value / price if price > 0 else Decimal("0.01")
        
        logger.info(f"📊 Balance: ${balance:,.2f} | Allocation: 50% | Margin: 30% | Leverage: {leverage:.2f}x")
        logger.info(f"📊 Position Value: ${position_value:,.2f} | Quantity: {quantity:.6f} BTC")
        
        return quantity
    
    def _calculate_unrealized_pnl(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized PnL for current position"""
        if self.position_state.side == "FLAT" or not self.position_state.entry_price:
            return Decimal("0")
        
        if self.position_state.side == "LONG":
            return (current_price - self.position_state.entry_price) * self.position_state.size
        else:  # SHORT
            return (self.position_state.entry_price - current_price) * self.position_state.size
    
    def process_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming TradingView alert with deduplication and proper flip logic"""
        
        # Handle user's TradingView alert format: {"event":"buy",...}
        action = alert_data.get('action', alert_data.get('event', '')).lower()
        symbol = alert_data.get('symbol', 'BTCUSDT')
        price = Decimal(str(alert_data.get('price', 0)))
        
        # Generate alert hash for deduplication
        alert_hash = self._get_alert_hash(alert_data)
        
        # Check for duplicates
        if self._is_duplicate_alert(alert_hash):
            return {
                "success": True,
                "status": "duplicate_ignored",
                "reason": f"Duplicate alert within {ALERT_DEDUP_WINDOW_SECONDS}s window",
                "alert_hash": alert_hash
            }
        
        # Update position state tracking
        self.position_state.last_alert_hash = alert_hash
        self.position_state.last_alert_time = datetime.now().isoformat()
        
        logger.info("=" * 60)
        logger.info(f"🚨 ALERT RECEIVED: {action.upper()} {symbol}")
        logger.info(f"💰 Price: ${price:,.2f}")
        logger.info(f"📍 Current Position: {self.position_state.side} {self.position_state.size} BTC")
        if self.position_state.entry_price:
            logger.info(f"💵 Entry Price: ${self.position_state.entry_price:,.2f}")
        
        # Calculate position size for new trades
        quantity = self._calculate_position_size(price)
        logger.info(f"📊 Trade Size: {quantity:.6f} BTC")
        
        # Determine what action to take based on current position
        current_side = self.position_state.side
        
        result = None
        
        # Case 1: Already in requested position - skip
        if action == 'buy' and current_side == "LONG":
            logger.info(f"⏭️  Already LONG, skipping BUY signal")
            result = {"success": True, "status": "skipped", "reason": "already_long"}
        
        elif action == 'sell' and current_side == "SHORT":
            logger.info(f"⏭️  Already SHORT, skipping SELL signal")
            result = {"success": True, "status": "skipped", "reason": "already_short"}
        
        # Case 2: Flat - open new position
        elif current_side == "FLAT":
            if action == 'buy':
                result = self._open_position(symbol, "LONG", quantity, price)
            elif action == 'sell':
                result = self._open_position(symbol, "SHORT", quantity, price)
        
        # Case 3: Opposite position - FLIP (close current + open new)
        elif (action == 'buy' and current_side == "SHORT") or \
             (action == 'sell' and current_side == "LONG"):
            result = self._flip_position(symbol, current_side, action, quantity, price)
        
        else:
            logger.warning(f"⚠️  Unhandled case: action={action}, current={current_side}")
            result = {"success": False, "error": f"Unhandled case: {action} while {current_side}"}
        
        # Save state after processing
        self._save_state()
        
        # Log the alert for debugging
        self._log_alert(alert_data, result, str(alert_data))
        
        logger.info("=" * 60)
        return result
    
    def _open_position(self, symbol: str, side: str, quantity: Decimal, price: Decimal) -> Dict[str, Any]:
        """Open a new position"""
        order_side = OrderSide.BUY if side == "LONG" else OrderSide.SELL
        
        result = self.engine.place_order(
            symbol=symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            market_price=price
        )
        
        if result.get('success'):
            # Update our state
            self.position_state.side = side
            self.position_state.size = quantity
            self.position_state.entry_price = price
            self.position_state.trades_count += 1
            self.position_state.last_trade_time = datetime.now().isoformat()
            
            logger.info(f"✅ OPENED {side} position: {quantity:.6f} BTC @ ${price:,.2f}")
            
            # Send Telegram notification
            if self.telegram.enabled:
                self.telegram.notify_position_open(
                    side=side,
                    symbol=symbol,
                    price=float(price),
                    size=float(quantity)
                )
        
        return result
    
    def _flip_position(self, symbol: str, current_side: str, action: str, 
                       new_quantity: Decimal, price: Decimal) -> Dict[str, Any]:
        """Flip position: close current and open opposite"""
        
        logger.info(f"🔄 FLIPPING POSITION: {current_side} → {'SHORT' if action == 'sell' else 'LONG'}")
        
        # Step 1: Close current position
        close_side = OrderSide.SELL if current_side == "LONG" else OrderSide.BUY
        close_qty = self.position_state.size
        
        close_result = self.engine.place_order(
            symbol=symbol,
            side=close_side,
            order_type=OrderType.MARKET,
            quantity=close_qty,
            market_price=price
        )
        
        if not close_result.get('success'):
            logger.error(f"❌ Failed to close {current_side} position: {close_result.get('error')}")
            return close_result
        
        # Calculate realized PnL from closing
        if current_side == "LONG":
            realized_pnl = (price - self.position_state.entry_price) * close_qty
        else:
            realized_pnl = (self.position_state.entry_price - price) * close_qty
        
        self.position_state.realized_pnl += realized_pnl
        logger.info(f"💰 Realized PnL from closing: ${realized_pnl:.4f}")
        
        # Step 2: Open new position in opposite direction
        new_side = "SHORT" if action == 'sell' else "LONG"
        open_side = OrderSide.SELL if action == 'sell' else OrderSide.BUY
        
        open_result = self.engine.place_order(
            symbol=symbol,
            side=open_side,
            order_type=OrderType.MARKET,
            quantity=new_quantity,
            market_price=price
        )
        
        if open_result.get('success'):
            self.position_state.side = new_side
            self.position_state.size = new_quantity
            self.position_state.entry_price = price
            self.position_state.trades_count += 1
            self.position_state.last_trade_time = datetime.now().isoformat()
            
            logger.info(f"✅ OPENED {new_side} position: {new_quantity:.6f} BTC @ ${price:,.2f}")
            logger.info(f"🎯 Position flip complete: {current_side} → {new_side}")
            
            # Send Telegram notification
            if self.telegram.enabled:
                self.telegram.notify_trade(
                    action=action,
                    symbol=symbol,
                    price=float(price),
                    size=float(new_quantity),
                    realized_pnl=float(realized_pnl),
                    from_side=current_side,
                    to_side=new_side
                )
        else:
            # If open failed, we're flat
            self.position_state.side = "FLAT"
            self.position_state.size = Decimal("0")
            self.position_state.entry_price = None
            logger.error(f"❌ Failed to open {new_side} position: {open_result.get('error')}")
        
        return {
            "success": True,
            "status": "position_flipped",
            "from_side": current_side,
            "to_side": new_side,
            "close_result": close_result,
            "open_result": open_result,
            "realized_pnl": str(realized_pnl)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status with complete statistics"""
        # Get current price for unrealized PnL calculation
        current_price = Decimal("71500")  # Placeholder - would fetch from API
        unrealized_pnl = self._calculate_unrealized_pnl(current_price)
        total_pnl = self.position_state.realized_pnl + unrealized_pnl
        
        # Calculate win/loss stats
        trades = self.engine.get_trade_history()
        winning_trades = len([t for t in trades if t.realized_pnl > 0])
        losing_trades = len([t for t in trades if t.realized_pnl < 0])
        total_trades = winning_trades + losing_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate average PnL
        avg_win = sum([float(t.realized_pnl) for t in trades if t.realized_pnl > 0]) / winning_trades if winning_trades > 0 else 0
        avg_loss = sum([float(t.realized_pnl) for t in trades if t.realized_pnl < 0]) / losing_trades if losing_trades > 0 else 0
        
        # Get current balance
        current_balance = self.engine.simulated_balance
        initial_balance = Decimal("10000.0")
        total_return_pct = ((current_balance - initial_balance) / initial_balance * 100) if initial_balance > 0 else 0
        
        # Check for recent alert log entries
        recent_alerts = self._get_recent_alert_log()
        
        return {
            "bot": {
                "alerts_received": len(self.recent_alerts),
                "trades_executed": self.position_state.trades_count,
                "last_alert": {
                    "time": self.position_state.last_alert_time,
                    "hash": self.position_state.last_alert_hash
                } if self.position_state.last_alert_time else None,
                "last_trade": {
                    "time": self.position_state.last_trade_time
                } if self.position_state.last_trade_time else None,
                "start_time": self.position_state.to_dict().get('start_time', datetime.now().isoformat()),
                "status": "running",
                "dedup_window_seconds": ALERT_DEDUP_WINDOW_SECONDS,
                "recent_webhook_logs": recent_alerts
            },
            "position": {
                "symbol": self.position_state.symbol,
                "side": self.position_state.side,
                "size": str(self.position_state.size),
                "entry_price": str(self.position_state.entry_price) if self.position_state.entry_price else None,
                "unrealized_pnl": str(unrealized_pnl),
                "realized_pnl": str(self.position_state.realized_pnl),
                "total_pnl": str(total_pnl),
                "current_balance": str(current_balance),
                "initial_balance": str(initial_balance)
            },
            "performance": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": f"{win_rate:.1f}%",
                "avg_win": f"${avg_win:,.2f}",
                "avg_loss": f"${avg_loss:,.2f}",
                "realized_pnl": f"${float(self.position_state.realized_pnl):,.2f}",
                "unrealized_pnl": f"${float(unrealized_pnl):,.2f}",
                "total_pnl": f"${float(total_pnl):,.2f}",
                "total_return_pct": f"{float(total_return_pct):,.2f}%",
                "current_balance": f"${float(current_balance):,.2f}",
                "initial_balance": f"${float(initial_balance):,.2f}"
            },
            "configuration": {
                "symbol": self.config.symbol,
                "position_allocation": f"{self.config.position_allocation_percent*100:.0f}%",
                "margin_percent": f"{self.config.margin_percent*100:.0f}%",
                "effective_leverage": f"{1/self.config.margin_percent:.1f}x",
                "paper_mode": self.config.paper_mode,
                "mode": "DRY-RUN" if self.config.paper_mode else "LIVE"
            }
        }
    
    def _get_recent_alert_log(self, limit: int = 5) -> list:
        """Get recent entries from alert log"""
        try:
            if not os.path.exists(ALERT_LOG_FILE):
                return []
            with open(ALERT_LOG_FILE, 'r') as f:
                lines = f.readlines()
            # Return last N entries
            recent = []
            for line in lines[-limit:]:
                try:
                    recent.append(json.loads(line.strip()))
                except:
                    pass
            return recent
        except Exception as e:
            return [{"error": str(e)}]
    
    def reset_position(self, side: str = "FLAT", size: str = "0", entry_price: Optional[str] = None):
        """Manually reset position state (for fixing corrupted state)"""
        self.position_state.side = side
        self.position_state.size = Decimal(str(size))
        self.position_state.entry_price = Decimal(str(entry_price)) if entry_price else None
        self._save_state()
        
        # Also reset engine position
        from dry_run_engine import SimulatedPosition, PositionSide
        if side == "FLAT":
            if self.position_state.symbol in self.engine.positions:
                del self.engine.positions[self.position_state.symbol]
        else:
            pos = SimulatedPosition(
                symbol=self.position_state.symbol,
                side=PositionSide(side),
                size=self.position_state.size,
                entry_price=self.position_state.entry_price
            )
            self.engine.positions[self.position_state.symbol] = pos
        
        logger.info(f"🔄 Position manually reset to: {side} {size} BTC @ {entry_price}")


# Global bot instance
bot: Optional[TradingBot] = None


class WebhookHandler(BaseHTTPRequestHandler):
    """Handle webhook alerts from TradingView"""
    
    def log_message(self, format, *args):
        logger.info(format % args)
    
    def do_POST(self):
        if self.path == '/webhook':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            raw_body = post_data.decode('utf-8')
            
            # Log EVERY webhook request for debugging
            client_ip = self.client_address[0]
            logger.info(f"🔔 WEBHOOK RECEIVED from {client_ip}")
            logger.info(f"📄 Raw body: {raw_body[:500]}")  # Log first 500 chars
            
            try:
                alert_data = json.loads(raw_body)
                result = bot.process_alert(alert_data)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result, indent=2).encode())
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parse error: {e}")
                logger.error(f"❌ Raw data received: {raw_body[:500]}")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Invalid JSON", "raw": raw_body[:200]}).encode())
            except Exception as e:
                logger.error(f"❌ Error processing alert: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Trading Bot Webhook - Send POST to /webhook\n')
        elif self.path == '/status':
            status = bot.get_status() if bot else {"status": "not_initialized"}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status, indent=2).encode())
        elif self.path == '/webhook':
            # Allow GET to webhook for testing
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "webhook_ready",
                "message": "Send POST requests to this URL with JSON: {\"action\":\"buy|sell\",\"symbol\":\"BTCUSDT\",\"price\":12345}"
            }, indent=2).encode())
        else:
            self.send_response(404)
            self.end_headers()


class DashboardHandler(BaseHTTPRequestHandler):
    """Serve monitoring dashboard"""
    
    def log_message(self, format, *args):
        pass  # Reduce noise
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_dashboard()
        elif parsed_path.path == '/api/status':
            self.serve_api_status()
        elif parsed_path.path == '/api/trades':
            self.serve_api_trades()
        elif parsed_path.path == '/api/reset':
            self.handle_reset()
        else:
            self.send_response(404)
            self.end_headers()
    
    def serve_dashboard(self):
        status = bot.get_status()
        
        # Format numbers nicely
        pos_size = float(status['position']['size']) if status['position']['size'] else 0
        entry_price = float(status['position']['entry_price']) if status['position']['entry_price'] else 0
        position_value = pos_size * entry_price if pos_size and entry_price else 0
        unrealized_pnl = float(status['position']['unrealized_pnl']) if status['position']['unrealized_pnl'] else 0
        realized_pnl = float(status['position']['realized_pnl']) if status['position']['realized_pnl'] else 0
        
        # Format side display
        side = status['position']['side']
        side_class = 'position-long' if side == 'LONG' else 'position-short' if side == 'SHORT' else 'position-flat'
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>TradingBot Dashboard</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #fff;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #00d4aa;
            border-bottom: 2px solid #00d4aa;
            padding-bottom: 10px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .card {{
            background: #151b3d;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2a3362;
        }}
        .card h2 {{
            margin-top: 0;
            color: #8892b0;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .metric {{
            font-size: 32px;
            font-weight: bold;
            color: #00d4aa;
        }}
        .metric.red {{
            color: #ff6b6b;
        }}
        .metric.yellow {{
            color: #ffd93d;
        }}
        .metric.large {{
            font-size: 28px;
        }}
        .detail {{
            margin-top: 10px;
            font-size: 14px;
            color: #8892b0;
            line-height: 1.6;
        }}
        .detail strong {{
            color: #fff;
        }}
        .position-long {{
            color: #00d4aa;
            font-weight: bold;
        }}
        .position-short {{
            color: #ff6b6b;
            font-weight: bold;
        }}
        .position-flat {{
            color: #8892b0;
        }}
        .pnl-positive {{
            color: #00d4aa;
        }}
        .pnl-negative {{
            color: #ff6b6b;
        }}
        .status-indicator {{
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #00d4aa;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-dryrun {{
            background: #ffd93d;
            color: #0a0e27;
        }}
        .price-large {{
            font-size: 24px;
            font-weight: bold;
            color: #fff;
        }}
        .warning {{
            background: #ff6b6b;
            color: #fff;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        /* P&L Visual Styles */
        .pnl-card {{
            position: relative;
            overflow: hidden;
        }}
        .pnl-card.positive {{
            border-left: 4px solid #00d4aa;
            background: linear-gradient(135deg, #151b3d 0%, #0d2b1f 100%);
        }}
        .pnl-card.negative {{
            border-left: 4px solid #ff6b6b;
            background: linear-gradient(135deg, #151b3d 0%, #2b0d0d 100%);
        }}
        .pnl-card.neutral {{
            border-left: 4px solid #8892b0;
        }}
        .pnl-amount {{
            font-size: 42px;
            font-weight: bold;
            margin: 15px 0;
        }}
        .pnl-amount.positive {{
            color: #00d4aa;
        }}
        .pnl-amount.negative {{
            color: #ff6b6b;
        }}
        .pnl-amount.neutral {{
            color: #8892b0;
        }}
        .pnl-icon {{
            font-size: 24px;
            margin-right: 10px;
        }}
        .pnl-label {{
            font-size: 12px;
            color: #8892b0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .pnl-sublabel {{
            font-size: 13px;
            color: #6b7280;
            margin-top: 8px;
        }}
        .summary-bar {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .summary-item {{
            background: #1a1f3d;
            padding: 15px 25px;
            border-radius: 10px;
            text-align: center;
            min-width: 120px;
        }}
        .summary-value {{
            font-size: 24px;
            font-weight: bold;
            color: #fff;
        }}
        .summary-label {{
            font-size: 11px;
            color: #8892b0;
            text-transform: uppercase;
            margin-top: 5px;
        }}
        .trade-history {{
            margin-top: 15px;
        }}
        .trade-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 15px;
            background: #1a1f3d;
            border-radius: 8px;
            margin-bottom: 8px;
        }}
        .trade-side {{
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
        }}
        .trade-side.buy {{
            background: #00d4aa22;
            color: #00d4aa;
        }}
        .trade-side.sell {{
            background: #ff6b6b22;
            color: #ff6b6b;
        }}
        .trade-pnl {{
            font-weight: bold;
            font-size: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <span class="status-indicator"></span>
            TradingBot Dashboard
            <span class="badge badge-dryrun">DRY-RUN MODE</span>
        </h1>
        
        <!-- Summary Bar -->
        <div class="summary-bar">
            <div class="summary-item">
                <div class="summary-value {side_class}">{side}</div>
                <div class="summary-label">Position</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{pos_size:.4f}</div>
                <div class="summary-label">BTC Size</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">${entry_price:,.0f}</div>
                <div class="summary-label">Entry Price</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{status['performance']['total_trades']}</div>
                <div class="summary-label">Trades</div>
            </div>
        </div>
        
        <!-- P&L Grid -->
        <div class="grid">
            <!-- Unrealized PnL Card -->
            <div class="card pnl-card {'positive' if unrealized_pnl > 0 else 'negative' if unrealized_pnl < 0 else 'neutral'}">
                <div class="pnl-label">
                    <span class="pnl-icon">{'&#9650;' if unrealized_pnl >= 0 else '&#9660;'}</span>
                    OPEN POSITION P&L
                </div>
                <div class="pnl-amount {'positive' if unrealized_pnl > 0 else 'negative' if unrealized_pnl < 0 else 'neutral'}">
                    {'+' if unrealized_pnl > 0 else ''}${unrealized_pnl:,.2f}
                </div>
                <div class="pnl-sublabel">
                    Current trade profit/loss (not realized yet)<br>
                    <strong>Entry:</strong> ${entry_price:,.2f} | 
                    <strong>Size:</strong> {pos_size:.6f} BTC
                </div>
            </div>
            
            <!-- Realized PnL Card -->
            <div class="card pnl-card {'positive' if realized_pnl > 0 else 'negative' if realized_pnl < 0 else 'neutral'}">
                <div class="pnl-label">
                    <span class="pnl-icon">&#36;</span>
                    CLOSED TRADES P&L
                </div>
                <div class="pnl-amount {'positive' if realized_pnl > 0 else 'negative' if realized_pnl < 0 else 'neutral'}">
                    {'+' if realized_pnl > 0 else ''}${realized_pnl:,.2f}
                </div>
                <div class="pnl-sublabel">
                    Profit/loss from completed trades<br>
                    <strong>Total Trades:</strong> {status['performance']['total_trades']}
                </div>
            </div>
        </div>
        
        <!-- Combined Total -->
        <div class="card" style="margin-top: 20px; text-align: center; background: {'linear-gradient(135deg, #0d2b1f 0%, #151b3d 100%)' if (realized_pnl + unrealized_pnl) >= 0 else 'linear-gradient(135deg, #2b0d0d 0%, #151b3d 100%)'};">
            <div class="pnl-label">TOTAL P&L (Realized + Unrealized)</div>
            <div class="pnl-amount {'positive' if (realized_pnl + unrealized_pnl) >= 0 else 'negative'}" style="font-size: 56px;">
                {'+' if (realized_pnl + unrealized_pnl) > 0 else ''}${realized_pnl + unrealized_pnl:,.2f}
            </div>
        </div>
        
        <!-- Trade History -->
        <div class="card" style="margin-top: 20px;">
            <h2>RECENT TRADE HISTORY</h2>
            <div class="trade-history">
                {self._render_trade_history()}
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h2>📊 COMPLETE STATISTICS</h2>
            <div class="detail">
                <strong>Initial Balance:</strong> $10,000.00<br>
                <strong>Current Balance:</strong> ${float(status['position'].get('current_balance', 10000)):,.2f}<br>
                <strong>Total Return:</strong> {status['performance'].get('total_return_pct', '0.00%')}<br>
                <br>
                <strong>Total Trades:</strong> {status['performance']['total_trades']}<br>
                <strong>Winning Trades:</strong> {status['performance'].get('winning_trades', 0)}<br>
                <strong>Losing Trades:</strong> {status['performance'].get('losing_trades', 0)}<br>
                <strong>Win Rate:</strong> {status['performance'].get('win_rate', '0.0%')}<br>
                <br>
                <strong>Average Win:</strong> {status['performance'].get('avg_win', '$0.00')}<br>
                <strong>Average Loss:</strong> {status['performance'].get('avg_loss', '$0.00')}<br>
                <br>
                <strong>Position Allocation:</strong> 50% of balance<br>
                <strong>Margin:</strong> 30%<br>
                <strong>Effective Leverage:</strong> ~3.3x<br>
                <strong>Symbol:</strong> BTCUSDT<br>
                <strong>Mode:</strong> {status['configuration'].get('mode', 'DRY-RUN')}<br>
                <strong>State File:</strong> {STATE_FILE}
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_api_status(self):
        status = bot.get_status()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status, indent=2).encode())
    
    def serve_api_trades(self):
        trades = bot.engine.get_trade_history()
        trade_list = [{
            "id": t.trade_id,
            "symbol": t.symbol,
            "side": t.side.value,
            "quantity": str(t.quantity),
            "price": str(t.price),
            "pnl": str(t.realized_pnl),
            "time": datetime.fromtimestamp(t.timestamp_ms/1000).isoformat()
        } for t in trades]
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(trade_list, indent=2).encode())
    
    def _render_trade_history(self) -> str:
        """Render recent trades as HTML"""
        try:
            if not os.path.exists(ALERT_LOG_FILE):
                return '<div class="detail">No trades yet</div>'
            
            with open(ALERT_LOG_FILE, 'r') as f:
                lines = f.readlines()
            
            trades = []
            for line in reversed(lines[-10:]):  # Last 10 entries, newest first
                try:
                    entry = json.loads(line.strip())
                    result = entry.get('result', {})
                    if 'realized_pnl' in result:
                        alert = entry.get('parsed_alert', {})
                        pnl = float(result.get('realized_pnl', 0))
                        trades.append({
                            'time': entry.get('timestamp', 'N/A')[:16].replace('T', ' '),
                            'action': alert.get('action', 'N/A').upper(),
                            'price': float(alert.get('price', 0)),
                            'pnl': pnl
                        })
                except:
                    continue
            
            if not trades:
                return '<div class="detail">No completed trades yet</div>'
            
            html = ''
            for t in trades[:5]:  # Show last 5
                pnl_class = 'positive' if t['pnl'] >= 0 else 'negative'
                pnl_sign = '+' if t['pnl'] > 0 else ''
                html += f'''
                <div class="trade-item">
                    <div>
                        <span class="trade-side {'buy' if t['action'] == 'BUY' else 'sell'}">{t['action']}</span>
                        <span style="color: #8892b0; margin-left: 10px;">@ ${t['price']:,.2f}</span>
                    </div>
                    <div class="trade-pnl {pnl_class}">
                        {pnl_sign}${t['pnl']:,.2f}
                    </div>
                </div>
                '''
            return html
        except Exception as e:
            return f'<div class="detail">Error loading trades: {e}</div>'
    
    def handle_reset(self):
        """Handle manual position reset"""
        query = parse_qs(urlparse(self.path).query)
        side = query.get('side', ['FLAT'])[0]
        size = query.get('size', ['0'])[0]
        entry = query.get('entry', [None])[0]
        
        bot.reset_position(side, size, entry)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "success": True,
            "message": f"Position reset to {side} {size} BTC",
            "new_state": bot.get_status()['position']
        }, indent=2).encode())


def run_webhook_server(port=80):
    """Run webhook server in separate thread on port 80"""
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    logger.info(f"🚀 Webhook server on port {port}")
    server.serve_forever()


def run_dashboard_server(port=6000):
    """Run dashboard server in main thread"""
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    logger.info(f"📊 Dashboard on http://89.167.60.3:{port}")
    server.serve_forever()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🤖 TRADING BOT SERVER STARTING")
    logger.info("=" * 60)
    
    # Initialize bot (loads state from disk)
    bot = TradingBot()
    
    logger.info("=" * 60)
    logger.info("Mode: DRY-RUN (no real trades)")
    logger.info("Webhook: http://89.167.60.3/webhook (port 80)")
    logger.info("Dashboard: http://89.167.60.3:6000")
    logger.info("API Status: http://89.167.60.3:6000/api/status")
    logger.info("=" * 60)
    
    # Start webhook server in thread on port 80
    webhook_thread = threading.Thread(target=run_webhook_server, args=(80,), daemon=True)
    webhook_thread.start()
    
    # Start dashboard server in main thread
    try:
        run_dashboard_server(6000)
    except KeyboardInterrupt:
        logger.info("\n🛑 Server stopped")
        bot._save_state()
        logger.info("💾 State saved")
