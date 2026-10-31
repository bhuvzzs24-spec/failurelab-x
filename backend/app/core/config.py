import os
from functools import lru_cache
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./failurelab.db")
    broker_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    api_token: str = os.getenv("API_TOKEN", "local-development-token")
    control_token: str = os.getenv("CONTROL_TOKEN", "local-control-token")
    sandbox: str = os.getenv("SANDBOX_ID", "demo")
    gateway: str = os.getenv("GATEWAY_URL", "http://gateway:8000")
    proxy: str = os.getenv("PROXY_URL", "http://fault-proxy:8000")
    proxy_control: str = os.getenv("PROXY_CONTROL_URL", "http://fault-proxy:8001")
    order: str = os.getenv("ORDER_URL", "http://order:8000")
    payment: str = os.getenv("PAYMENT_URL", "http://payment:8000")
    inventory: str = os.getenv("INVENTORY_URL", "http://inventory:8000")
    version: str = os.getenv("BUILD_VERSION", "development")

    def __post_init__(self):
        from urllib.parse import urlsplit
        if self.sandbox != "demo": raise ValueError("Phase 1 supports only the managed demo sandbox")
        for field in ("gateway","proxy","proxy_control","order","payment","inventory"):
            value=urlsplit(getattr(self,field))
            expected="fault-proxy" if field.startswith("proxy") else field
            if value.scheme!="http" or value.hostname not in {expected,"localhost","127.0.0.1","::1"} or value.username or value.password or value.path not in {"","/"} or value.query or value.fragment:
                raise ValueError(f"{field} must be an operator-managed local sandbox origin")

@lru_cache
def settings() -> Settings:
    return Settings()

# Registration accepts logical identities only. Network destinations are operator configuration.
ALLOWED_SERVICES = {"gateway", "order", "payment", "inventory"}
