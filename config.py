import os
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Loglama ayarları
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("CryptoBot")

# Telegram Ayarları
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# İzin Verilen Kullanıcı ID'si (Güvenlik Koruması)
raw_user_id = os.getenv("ALLOWED_TELEGRAM_USER_ID", "0").strip()
try:
    ALLOWED_TELEGRAM_USER_ID = int(raw_user_id) if raw_user_id else 0
except ValueError:
    ALLOWED_TELEGRAM_USER_ID = 0

# Takip Listesi
raw_watchlist = os.getenv(
    "WATCHLIST",
    "BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,AVAX/USDT,XRP/USDT,NEAR/USDT,LINK/USDT"
)
WATCHLIST = [s.strip().upper() for s in raw_watchlist.split(",") if s.strip()]

# Tarama & İndikatör Ayarları
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "30"))
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30.0"))
RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", "70.0"))

# Portföy ve Risk Ayarları
PORTFOLIO_CAPITAL_USDT = float(os.getenv("PORTFOLIO_CAPITAL_USDT", "11000.0"))
DEFAULT_RISK_PERCENT = float(os.getenv("DEFAULT_RISK_PERCENT", "1.5"))

def is_authorized(user_id: int) -> bool:
    """Kullanıcının botu kullanma yetkisi olup olmadığını denetler."""
    if ALLOWED_TELEGRAM_USER_ID == 0:
        # Eğer henüz kullanıcı ID tanımlanmadıysa güvenlik için uyar ancak ilk kurulumda izin ver
        return True
    return user_id == ALLOWED_TELEGRAM_USER_ID
