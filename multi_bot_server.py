#!/usr/bin/env python3
"""
Multi-Bot Trading Server
Supports multiple strategies: DamjanBot1 (5min) and DamjanBot2 (15min)
- Single webhook endpoint receives alerts from both bots
- Separate state tracking for each bot
- Separate dashboards: /damjanbot1 and /damjanbot2
"""

import json
import logging
import os
import sys
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from dry_run_engine import DryRunEngine, OrderSide, OrderType
from telegram_notifier import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("MultiBot")

ALERT_DEDUP_WINDOW_SECONDS = 30


class BotInstance:
    """Individual bot instance for a specific strategy"""
    
    def __init__(self, bot_id: str, name: str, timeframe: str):
        self.bot_id = bot_id
        self.name = name
        self.timeframe = timeframe
        
        # State file per bot
        self.state_file = os.path.join(os.path.dirname(__file__), f'bot_state_{bot_id}.json')
        self.alert_log_file = os.path.join(os.path.dirname(__file__), f'alert_log_{bot_id}.jsonl')
        
        # Initialize config
        os.environ['BINANCE_API_KEY'] = 'dry_run_key'
        os.environ['BINANCE_SECRET_KEY'] = 'dry_run_secret'
        os.environ['PAPER_MODE'] = 'true'
        
        self.config = Config()
        self.engine = DryRunEngine(self.config)
        self.telegram = TelegramNotifier(
            bot_token=self.config.telegram_bot_token,
            chat_id=self.config.telegram_chat_id
        )
        
        # Position state
        self.symbol = "BTCUSDT"
        self.side = "FLAT"
        self.size = Decimal("0")
        self.entry_price = None
        self.realized_pnl = Decimal("0")
        self.trades_count = 0
        self.last_trade_time = None
        self.last_alert_time = None
        self.last_alert_hash = None
        
        # Dedup tracking
        self.recent_alerts: Dict[str, datetime] = {}
        
        # Load state
        self._load_state()
        
        logger.info(f"✅ {self.name} initialized ({self.timeframe})")
        logger.info(f"   State file: {self.state_file}")
    
    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                self.side = data.get('side', 'FLAT')
                self.size = Decimal(str(data.get('size', '0')))
                self.entry_price = Decimal(str(data['entry_price'])) if data.get('entry_price') else None
                self.realized_pnl = Decimal(str(data.get('realized_pnl', '0')))
                self.trades_count = data.get('trades_count', 0)
                self.last_trade_time = data.get('last_trade_time')
                logger.info(f"📂 {self.name}: Loaded state - {self.side}")
            except Exception as e:
                logger.warning(f"⚠️ {self.name}: Could not load state: {e}")
    
    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    'bot_id': self.bot_id,
                    'name': self.name,
                    'timeframe': self.timeframe,
                    'symbol': self.symbol,
                    'side': self.side,
                    'size': str(self.size),
                    'entry_price': str(self.entry_price) if self.entry_price else None,
                    'realized_pnl': str(self.realized_pnl),
                    'trades_count': self.trades_count,
                    'last_trade_time': self.last_trade_time,
                    'last_alert_time': self.last_alert_time,
                    'last_alert_hash': self.last_alert_hash
                }, f, indent=2)
        except Exception as e:
            logger.error(f"❌ {self.name}: Could not save state: {e}")
    
    def _get_alert_hash(self, alert_data: Dict) -> str:
        action = alert_data.get('action', alert_data.get('event', '')).lower()
        price = alert_data.get('price', 0)
        price_rounded = round(float(price)) if price else 0
        return f"{self.bot_id}:{action}:{price_rounded}"
    
    def _is_duplicate(self, alert_hash: str) -> bool:
        now = datetime.now()
        cutoff = now - timedelta(seconds=ALERT_DEDUP_WINDOW_SECONDS)
        self.recent_alerts = {h: t for h, t in self.recent_alerts.items() if t > cutoff}
        
        if alert_hash in self.recent_alerts:
            age = (now - self.recent_alerts[alert_hash]).total_seconds()
            logger.warning(f"⚠️ {self.name}: DUPLICATE detected ({age:.0f}s ago)")
            return True
        
        self.recent_alerts[alert_hash] = now
        return False
    
    def _calculate_position_size(self, price: Decimal) -> Decimal:
        balance = self.engine.simulated_balance
        allocation = Decimal("0.50")  # 50%
        margin = Decimal("0.30")      # 30%
        leverage = Decimal("1") / margin
        position_value = balance * allocation * leverage
        quantity = position_value / price if price > 0 else Decimal("0.01")
        return quantity
    
    def _calculate_unrealized_pnl(self, current_price: Decimal) -> Decimal:
        if self.side == "FLAT" or not self.entry_price:
            return Decimal("0")
        if self.side == "LONG":
            return (current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - current_price) * self.size
    
    def process_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        action = alert_data.get('action', alert_data.get('event', '')).lower()
        symbol = alert_data.get('symbol', 'BTCUSDT')
        price = Decimal(str(alert_data.get('price', 0)))
        
        alert_hash = self._get_alert_hash(alert_data)
        
        if self._is_duplicate(alert_hash):
            return {"success": True, "status": "duplicate_ignored", "bot": self.name}
        
        self.last_alert_time = datetime.now().isoformat()
        self.last_alert_hash = alert_hash
        
        logger.info(f"🚨 {self.name}: {action.upper()} {symbol} @ ${price:,.2f}")
        logger.info(f"   Current: {self.side} {self.size:.6f} BTC")
        
        quantity = self._calculate_position_size(price)
        result = None
        
        # Already in position
        if action == 'buy' and self.side == "LONG":
            result = {"success": True, "status": "skipped", "reason": "already_long", "bot": self.name}
        elif action == 'sell' and self.side == "SHORT":
            result = {"success": True, "status": "skipped", "reason": "already_short", "bot": self.name}
        
        # Flat - open new
        elif self.side == "FLAT":
            if action == 'buy':
                result = self._open_position(symbol, "LONG", quantity, price)
            elif action == 'sell':
                result = self._open_position(symbol, "SHORT", quantity, price)
        
        # Flip position
        elif (action == 'buy' and self.side == "SHORT") or (action == 'sell' and self.side == "LONG"):
            result = self._flip_position(symbol, self.side, action, quantity, price)
        
        else:
            result = {"success": False, "error": f"Unhandled: {action} while {self.side}", "bot": self.name}
        
        self._save_state()
        self._log_alert(alert_data, result)
        
        return result
    
    def _open_position(self, symbol: str, side: str, quantity: Decimal, price: Decimal) -> Dict:
        order_side = OrderSide.BUY if side == "LONG" else OrderSide.SELL
        
        result = self.engine.place_order(
            symbol=symbol, side=order_side, order_type=OrderType.MARKET,
            quantity=quantity, market_price=price
        )
        
        if result.get('success'):
            self.side = side
            self.size = quantity
            self.entry_price = price
            self.trades_count += 1
            self.last_trade_time = datetime.now().isoformat()
            logger.info(f"✅ {self.name}: OPENED {side} {quantity:.6f} BTC @ ${price:,.2f}")
        
        return {**result, "bot": self.name, "status": "opened", "side": side}
    
    def _flip_position(self, symbol: str, current_side: str, action: str, 
                       new_quantity: Decimal, price: Decimal) -> Dict:
        logger.info(f"🔄 {self.name}: FLIPPING {current_side} → {'SHORT' if action == 'sell' else 'LONG'}")
        
        # Close current
        close_side = OrderSide.SELL if current_side == "LONG" else OrderSide.BUY
        close_result = self.engine.place_order(
            symbol=symbol, side=close_side, order_type=OrderType.MARKET,
            quantity=self.size, market_price=price
        )
        
        if not close_result.get('success'):
            return {**close_result, "bot": self.name, "status": "close_failed"}
        
        # Calculate PnL
        if current_side == "LONG":
            realized_pnl = (price - self.entry_price) * self.size
        else:
            realized_pnl = (self.entry_price - price) * self.size
        
        self.realized_pnl += realized_pnl
        logger.info(f"💰 {self.name}: Realized PnL: ${realized_pnl:.4f}")
        
        # Open new
        new_side = "SHORT" if action == 'sell' else "LONG"
        open_side = OrderSide.SELL if action == 'sell' else OrderSide.BUY
        
        open_result = self.engine.place_order(
            symbol=symbol, side=open_side, order_type=OrderType.MARKET,
            quantity=new_quantity, market_price=price
        )
        
        if open_result.get('success'):
            self.side = new_side
            self.size = new_quantity
            self.entry_price = price
            self.trades_count += 1
            self.last_trade_time = datetime.now().isoformat()
            logger.info(f"✅ {self.name}: OPENED {new_side} {new_quantity:.6f} BTC")
        
        return {
            "success": True,
            "status": "position_flipped",
            "bot": self.name,
            "from_side": current_side,
            "to_side": new_side,
            "realized_pnl": str(realized_pnl)
        }
    
    def _log_alert(self, alert_data: Dict, result: Dict):
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "bot": self.name,
                "alert": alert_data,
                "result": result,
                "position_before": self.side
            }
            with open(self.alert_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.warning(f"Could not log alert: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        current_price = Decimal("80000")  # Placeholder
        unrealized_pnl = self._calculate_unrealized_pnl(current_price)
        total_pnl = self.realized_pnl + unrealized_pnl
        
        trades = self.engine.get_trade_history()
        winning = len([t for t in trades if t.realized_pnl > 0])
        losing = len([t for t in trades if t.realized_pnl < 0])
        total = winning + losing
        win_rate = (winning / total * 100) if total > 0 else 0
        
        return {
            "bot": {
                "id": self.bot_id,
                "name": self.name,
                "timeframe": self.timeframe,
                "trades_executed": self.trades_count,
                "last_trade_time": self.last_trade_time,
                "last_alert_time": self.last_alert_time,
                "status": "running"
            },
            "position": {
                "symbol": self.symbol,
                "side": self.side,
                "size": str(self.size),
                "entry_price": str(self.entry_price) if self.entry_price else None,
                "unrealized_pnl": str(unrealized_pnl),
                "realized_pnl": str(self.realized_pnl),
                "total_pnl": str(total_pnl)
            },
            "performance": {
                "total_trades": total,
                "winning_trades": winning,
                "losing_trades": losing,
                "win_rate": f"{win_rate:.1f}%",
                "realized_pnl": f"${float(self.realized_pnl):,.2f}",
                "unrealized_pnl": f"${float(unrealized_pnl):,.2f}",
                "total_pnl": f"${float(total_pnl):,.2f}"
            }
        }


# Initialize both bots
bots: Dict[str, BotInstance] = {}


def init_bots():
    global bots
    bots = {
        "damjanbot1": BotInstance("damjanbot1", "DamjanBot1", "5m"),
        "damjanbot2": BotInstance("damjanbot2", "DamjanBot2", "15m")
    }
    logger.info("=" * 60)
    logger.info("🤖 MULTI-BOT SERVER READY")
    logger.info("=" * 60)


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(format % args)
    
    def do_POST(self):
        if self.path == '/webhook':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            raw_body = post_data.decode('utf-8')
            
            client_ip = self.client_address[0]
            logger.info(f"🔔 WEBHOOK from {client_ip}")
            
            try:
                alert_data = json.loads(raw_body)
                
                # Determine which bot based on alert content
                # Check for bot identifier in the alert
                bot_id = None
                
                # Method 1: Check if message contains bot name
                raw_str = raw_body.lower()
                if 'damjanbot1' in raw_str:
                    bot_id = 'damjanbot1'
                elif 'damjanbot2' in raw_str:
                    bot_id = 'damjanbot2'
                
                # Method 2: Check strategy field
                if not bot_id:
                    strategy = alert_data.get('strategy', '').lower()
                    if strategy == 'v1':
                        bot_id = 'damjanbot1'
                    elif strategy == 'v2w':
                        bot_id = 'damjanbot2'
                
                # Method 3: Default based on action field name
                if not bot_id:
                    # If uses 'action' -> Bot1, if uses 'event' -> Bot2
                    if 'action' in alert_data:
                        bot_id = 'damjanbot1'
                    elif 'event' in alert_data:
                        bot_id = 'damjanbot2'
                
                if bot_id and bot_id in bots:
                    result = bots[bot_id].process_alert(alert_data)
                    result['bot_id'] = bot_id
                else:
                    # Try all bots if can't determine
                    results = {}
                    for bid, bot in bots.items():
                        results[bid] = bot.process_alert(alert_data)
                    result = {"success": True, "multi_processed": True, "results": results}
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result, indent=2).encode())
                
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>DamJanBot Multi-Bot Server</title></head>
            <body style="font-family: Arial; padding: 40px; background: #0a0e27; color: white;">
                <h1>🤖 DamJanBot Multi-Bot Server</h1>
                <h2>Active Bots:</h2>
                <ul>
                    <li><a href="/damjanbot1" style="color: #00d4aa; font-size: 20px;">📊 DamjanBot1 Dashboard (5min)</a></li>
                    <li><a href="/damjanbot2" style="color: #00d4aa; font-size: 20px;">📊 DamjanBot2 Dashboard (15min)</a></li>
                </ul>
                <h2>API Endpoints:</h2>
                <ul>
                    <li><code>POST /webhook</code> - Receive TradingView alerts</li>
                    <li><code>GET /damjanbot1/api/status</code> - Bot1 status (JSON)</li>
                    <li><code>GET /damjanbot2/api/status</code> - Bot2 status (JSON)</li>
                </ul>
                <p>Webhook URL: <code>http://89.167.60.3/webhook</code></p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Route to specific bot dashboard
        if path == '/damjanbot1':
            self.serve_dashboard('damjanbot1')
        elif path == '/damjanbot2':
            self.serve_dashboard('damjanbot2')
        elif path == '/damjanbot1/api/status':
            self.serve_api_status('damjanbot1')
        elif path == '/damjanbot2/api/status':
            self.serve_api_status('damjanbot2')
        elif path == '/':
            self.serve_main_page()
        else:
            self.send_response(404)
            self.end_headers()
    
    def serve_main_page(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>DamJanBot - Multi Bot Dashboard</title>
            <meta http-equiv="refresh" content="10">
            <style>
                body { font-family: Arial; background: #0a0e27; color: white; padding: 40px; }
                h1 { color: #00d4aa; }
                .bot-card { background: #151b3d; padding: 30px; margin: 20px 0; border-radius: 15px; border: 1px solid #2a3362; }
                .bot-name { font-size: 24px; color: #00d4aa; margin-bottom: 10px; }
                .bot-info { color: #8892b0; margin-bottom: 15px; }
                .metric { display: inline-block; margin: 10px 20px 10px 0; }
                .metric-value { font-size: 28px; font-weight: bold; color: white; }
                .metric-label { font-size: 12px; color: #8892b0; text-transform: uppercase; }
                .btn { display: inline-block; padding: 12px 30px; background: #00d4aa; color: #0a0e27; 
                       text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 15px; }
                .position-long { color: #00d4aa; }
                .position-short { color: #ff6b6b; }
                .position-flat { color: #8892b0; }
            </style>
        </head>
        <body>
            <h1>🤖 DamJanBot - Multi Bot Dashboard</h1>
            <p style="color: #8892b0;">Monitor both your trading strategies in real-time</p>
        """
        
        for bot_id, bot in bots.items():
            status = bot.get_status()
            pos = status['position']
            perf = status['performance']
            side_class = f"position-{pos['side'].lower()}"
            
            html += f"""
            <div class="bot-card">
                <div class="bot-name">{bot.name}</div>
                <div class="bot-info">Timeframe: {bot.timeframe} | Symbol: {pos['symbol']}</div>
                
                <div class="metric">
                    <div class="metric-value {side_class}">{pos['side']}</div>
                    <div class="metric-label">Position</div>
                </div>
                
                <div class="metric">
                    <div class="metric-value">${float(pos['realized_pnl']):,.2f}</div>
                    <div class="metric-label">Realized PnL</div>
                </div>
                
                <div class="metric">
                    <div class="metric-value">{perf['win_rate']}</div>
                    <div class="metric-label">Win Rate</div>
                </div>
                
                <div class="metric">
                    <div class="metric-value">{perf['total_trades']}</div>
                    <div class="metric-label">Trades</div>
                </div>
                
                <br>
                <a href="/{bot_id}" class="btn">View Full Dashboard</a>
                <a href="/{bot_id}/api/status" class="btn" style="background: #2a3362; color: white; margin-left: 10px;">API Status</a>
            </div>
            """
        
        html += """
            <div style="margin-top: 40px; padding: 20px; background: #1a1f3d; border-radius: 10px;">
                <h3>Webhook Configuration</h3>
                <p>URL: <code style="background: #0a0e27; padding: 5px 10px; border-radius: 5px;">http://89.167.60.3/webhook</code></p>
                <p>Both bots use the same webhook endpoint. The bot automatically detects which strategy sent the alert.</p>
            </div>
        </body>
        </html>
        """
        
        self.wfile.write(html.encode())
    
    def serve_dashboard(self, bot_id: str):
        if bot_id not in bots:
            self.send_response(404)
            self.end_headers()
            return
        
        bot = bots[bot_id]
        status = bot.get_status()
        pos = status['position']
        perf = status['performance']
        
        side = pos['side']
        side_class = 'position-long' if side == 'LONG' else 'position-short' if side == 'SHORT' else 'position-flat'
        
        unrealized = float(pos['unrealized_pnl'])
        realized = float(pos['realized_pnl'])
        total = unrealized + realized
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{bot.name} Dashboard</title>
            <meta http-equiv="refresh" content="5">
            <style>
                body {{ font-family: Arial; background: #0a0e27; color: white; padding: 20px; margin: 0; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                h1 {{ color: #00d4aa; border-bottom: 2px solid #00d4aa; padding-bottom: 10px; }}
                .back {{ color: #8892b0; text-decoration: none; margin-bottom: 20px; display: inline-block; }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 20px; }}
                .card {{ background: #151b3d; padding: 20px; border-radius: 12px; border: 1px solid #2a3362; }}
                .card h2 {{ margin-top: 0; color: #8892b0; font-size: 14px; text-transform: uppercase; }}
                .metric {{ font-size: 36px; font-weight: bold; color: #00d4aa; }}
                .metric.red {{ color: #ff6b6b; }}
                .position-long {{ color: #00d4aa; }}
                .position-short {{ color: #ff6b6b; }}
                .position-flat {{ color: #8892b0; }}
                .detail {{ color: #8892b0; margin-top: 10px; line-height: 1.6; }}
                .detail strong {{ color: white; }}
                .pnl-positive {{ color: #00d4aa; }}
                .pnl-negative {{ color: #ff6b6b; }}
                .summary-bar {{ display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }}
                .summary-item {{ background: #1a1f3d; padding: 15px 25px; border-radius: 10px; text-align: center; }}
                .summary-value {{ font-size: 24px; font-weight: bold; }}
                .summary-label {{ font-size: 11px; color: #8892b0; text-transform: uppercase; margin-top: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <a href="/" class="back">← Back to Main Dashboard</a>
                <h1>{bot.name} Dashboard ({bot.timeframe})</h1>
                
                <div class="summary-bar">
                    <div class="summary-item">
                        <div class="summary-value {side_class}">{side}</div>
                        <div class="summary-label">Position</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value">{float(pos['size']):.4f}</div>
                        <div class="summary-label">BTC Size</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value">${float(pos['entry_price']) if pos['entry_price'] else 0:,.0f}</div>
                        <div class="summary-label">Entry Price</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value">{perf['total_trades']}</div>
                        <div class="summary-label">Trades</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value">{perf['win_rate']}</div>
                        <div class="summary-label">Win Rate</div>
                    </div>
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h2>Unrealized PnL</h2>
                        <div class="metric {'pnl-positive' if unrealized >= 0 else 'pnl-negative'}">
                            {'+' if unrealized > 0 else ''}${unrealized:,.2f}
                        </div>
                        <div class="detail">Current open position</div>
                    </div>
                    
                    <div class="card">
                        <h2>Realized PnL</h2>
                        <div class="metric {'pnl-positive' if realized >= 0 else 'pnl-negative'}">
                            {'+' if realized > 0 else ''}${realized:,.2f}
                        </div>
                        <div class="detail">Closed trades profit/loss</div>
                    </div>
                </div>
                
                <div class="card" style="margin-top: 20px; text-align: center;">
                    <h2>Total PnL (Realized + Unrealized)</h2>
                    <div class="metric {'pnl-positive' if total >= 0 else 'pnl-negative'}" style="font-size: 48px;">
                        {'+' if total > 0 else ''}${total:,.2f}
                    </div>
                </div>
                
                <div class="card" style="margin-top: 20px;">
                    <h2>Statistics</h2>
                    <div class="detail">
                        <strong>Winning Trades:</strong> {perf['winning_trades']}<br>
                        <strong>Losing Trades:</strong> {perf['losing_trades']}<br>
                        <strong>Total Trades:</strong> {perf['total_trades']}<br>
                        <strong>Configuration:</strong> 50% allocation, 30% margin, ~3.3x leverage<br>
                        <strong>Mode:</strong> DRY-RUN (Paper Trading)
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
    
    def serve_api_status(self, bot_id: str):
        if bot_id not in bots:
            self.send_response(404)
            self.end_headers()
            return
        
        status = bots[bot_id].get_status()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status, indent=2).encode())


def run_webhook_server(port=80):
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    logger.info(f"🚀 Webhook server on port {port}")
    server.serve_forever()


def run_dashboard_server(port=8080):
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    logger.info(f"📊 Dashboard on http://89.167.60.3:{port}")
    server.serve_forever()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🤖 MULTI-BOT SERVER STARTING")
    logger.info("=" * 60)
    
    init_bots()
    
    logger.info("=" * 60)
    logger.info("Webhook: http://89.167.60.3/webhook")
    logger.info("Main Dashboard: http://89.167.60.3:8080")
    logger.info("Bot1 Dashboard: http://89.167.60.3:8080/damjanbot1")
    logger.info("Bot2 Dashboard: http://89.167.60.3:8080/damjanbot2")
    logger.info("=" * 60)
    
    webhook_thread = threading.Thread(target=run_webhook_server, args=(80,), daemon=True)
    webhook_thread.start()
    
    try:
        run_dashboard_server(8080)
    except KeyboardInterrupt:
        logger.info("\n🛑 Server stopped")
