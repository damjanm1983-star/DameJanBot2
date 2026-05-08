import os
import logging
from typing import Any

class Config:
    def __init__(self):
        # Core Binance keys
        self.binance_api_key = os.getenv("BINANCE_API_KEY")
        self.binance_secret_key = os.getenv("BINANCE_SECRET_KEY")

        # Runtime mode
        self.paper_mode = os.getenv("PAPER_MODE", "false").lower() in ("true", "1", "yes")

        # Trading params (configurable)
        self.symbol = os.getenv("SYMBOL", "BTCUSDT")
        self.position_allocation_percent = float(os.getenv("POSITION_ALLOCATION_PERCENT", "0.50"))  # 50% of balance
        self.target_leverage = int(os.getenv("TARGET_LEVERAGE", "3"))
        self.max_notional_cap_usdt = float(os.getenv("MAX_NOTIONAL_CAP_USDT", "50000.0"))
        self.margin_percent = float(os.getenv("MARGIN_PERCENT", "0.30"))  # 30% margin

        # Startup safety
        self.startup_safe_mode = os.getenv("STARTUP_SAFE_MODE", "true").lower() in ("true", "1", "yes")

        # Logging / status
        self.log_path = os.getenv("LOG_FILE_PATH", "logs/binance_client.log")
        self.alert_log_path = os.getenv("ALERT_LOG_PATH", "logs/alerts.log")
        self.status_path = os.getenv("STATUS_FILE_PATH", "status.json")

        # Webhook (future)
        self.webhook_secret = os.getenv("WEBHOOK_SECRET", "")
        self.webhook_port = int(os.getenv("WEBHOOK_PORT", "8000"))

        # Timezone
        self.time_zone = os.getenv("TIME_ZONE", "UTC")

        # Telegram notifications
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.telegram_enabled = bool(self.telegram_bot_token and self.telegram_chat_id)

        self._validate()

        # Warning for live mode
        if not self.paper_mode:
            logging.getLogger(__name__).warning("LIVE mode engaged (PAPER_MODE is OFF). Ensure OP has reviewed risk.")

    def _validate(self):
        if not self.binance_api_key or not self.binance_secret_key:
            raise ValueError("BINANCE_API_KEY and BINANCE_SECRET_KEY must be set in environment.")
        if not (0 < self.position_allocation_percent <= 1.0):
            raise ValueError(f"POSITION_ALLOCATION_PERCENT must be between 0 and 1. Got: {self.position_allocation_percent}")
        if self.target_leverage <= 0:
            raise ValueError(f"TARGET_LEVERAGE must be positive. Got: {self.target_leverage}")
        if self.max_notional_cap_usdt <= 0:
            raise ValueError(f"MAX_NOTIONAL_CAP_USDT must be positive. Got: {self.max_notional_cap_usdt}")

# End
