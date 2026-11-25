import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App Environment
    APP_NAME: str = "Smart Grocery Inventory & Procurement Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True
    DEMO_MODE: bool = True

    # Database Configuration (MySQL support with automatic SQLite fallback)
    DATABASE_URL: str = Field(
        default="sqlite:///smart_grocery.db",
        description="SQLAlchemy DB URL (e.g., mysql+pymysql://user:pass@localhost:3306/grocery_db or sqlite:///smart_grocery.db)"
    )

    # Groq LLM Configuration
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Slack Integration Configuration
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_APP_TOKEN: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None

    # Slack Channel Names & IDs
    SLACK_INVENTORY_ALERTS_CHANNEL: str = "inventory-alerts"
    SLACK_ADMIN_APPROVALS_CHANNEL: str = "admin-approvals"
    SLACK_PURCHASE_ORDERS_CHANNEL: str = "purchase-orders"
    SLACK_SUPPLIER_UPDATES_CHANNEL: str = "supplier-updates"
    SLACK_INVENTORY_REPORTS_CHANNEL: str = "inventory-reports"

    # Authorized Role IDs
    ADMIN_USER_IDS: List[str] = Field(default_factory=lambda: ["U0CL03S65SR", "U_ADMIN_01", "U_ADMIN_DEMO"])
    SUPPLIER_USER_IDS: List[str] = Field(default_factory=lambda: ["U0CL94EJPU4", "U_SUPPLIER_APEX", "U_SUPPLIER_GOLDEN", "U_SUPPLIER_PUREOIL", "U_SUPPLIER_DEMO"])

    # Email / SMTP Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    ADMIN_EMAIL: str = "admin@groceryinventory.com"
    SUPPLIER_EMAIL: str = "orders@apexagro.com"
    EMAIL_NOTIFICATIONS_ENABLED: bool = True

    # Stock Monitoring Scheduler Configuration
    STOCK_MONITOR_INTERVAL_SECONDS: int = 30
    DEFAULT_LEAD_TIME_DAYS: int = 2
    SAFETY_STOCK_FACTOR: float = 1.25

    @property
    def is_slack_configured(self) -> bool:
        return bool(self.SLACK_BOT_TOKEN and self.SLACK_BOT_TOKEN.startswith("xoxb-"))

    @property
    def is_groq_configured(self) -> bool:
        return bool(self.GROQ_API_KEY and len(self.GROQ_API_KEY.strip()) > 10)

settings = Settings()
