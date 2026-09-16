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

# Genişletilmiş Varsayılan Takip Listesi (Piyasa değeri ve hacmi en yüksek 45 token)
DEFAULT_WATCHLIST = (
    "BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,XRP/USDT,DOGE/USDT,ADA/USDT,AVAX/USDT,SUI/USDT,"
    "LINK/USDT,NEAR/USDT,APT/USDT,DOT/USDT,PEPE/USDT,SHIB/USDT,UNI/USDT,FET/USDT,RENDER/USDT,"
    "AAVE/USDT,TAO/USDT,WIF/USDT,ICP/USDT,INJ/USDT,TIA/USDT,SEI/USDT,OP/USDT,ARB/USDT,"
    "BONK/USDT,POL/USDT,PENDLE/USDT,FLOKI/USDT,GALA/USDT,FTM/USDT,STX/USDT,ATOM/USDT,"
    "LDO/USDT,CRV/USDT,JUP/USDT,ONDO/USDT,ENA/USDT,KAS/USDT,WLD/USDT,MKR/USDT,RUNE/USDT"
)

raw_watchlist = os.getenv("WATCHLIST", DEFAULT_WATCHLIST)
WATCHLIST = [s.strip().upper() for s in raw_watchlist.split(",") if s.strip()]

# Dinamik En Çok İşlem Gören Tokenleri Tarama Ayarları
DYNAMIC_TOP_TOKENS = os.getenv("DYNAMIC_TOP_TOKENS", "true").lower() in ("true", "1", "yes")
TOP_TOKENS_LIMIT = int(os.getenv("TOP_TOKENS_LIMIT", "40"))

# Tarama & İndikatör Ayarları
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "15"))
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30.0"))
RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", "70.0"))

# Akıllı Bildirim & Soğuma (Cooldown / Spam Önleme) Ayarları
# Aynı token ve aynı sinyal tipi için bildirim tekrarı yapılmayacak minimum saat aralığı
ALERT_COOLDOWN_HOURS = float(os.getenv("ALERT_COOLDOWN_HOURS", "6.0"))

# Ani Çakılış ve Yükseliş Öncesi Erken Uyarı Ayarları
EARLY_WARNING_ENABLED = os.getenv("EARLY_WARNING_ENABLED", "true").lower() in ("true", "1", "yes")
VOLUME_SPIKE_MULTIPLIER = float(os.getenv("VOLUME_SPIKE_MULTIPLIER", "2.5"))  # 2.5 kat hacim patlaması
BOLLINGER_SQUEEZE_THRESHOLD = float(os.getenv("BOLLINGER_SQUEEZE_THRESHOLD", "0.045"))  # %4.5 altı sıkışma

# Portföy ve Risk Ayarları
PORTFOLIO_CAPITAL_USDT = float(os.getenv("PORTFOLIO_CAPITAL_USDT", "11000.0"))
DEFAULT_RISK_PERCENT = float(os.getenv("DEFAULT_RISK_PERCENT", "1.5"))

def is_authorized(user_id: int) -> bool:
    """Kullanıcının botu kullanma yetkisi olup olmadığını denetler."""
    if ALLOWED_TELEGRAM_USER_ID == 0:
        # Eğer henüz kullanıcı ID tanımlanmadıysa güvenlik için uyar ancak ilk kurulumda izin ver
        return True
    return user_id == ALLOWED_TELEGRAM_USER_ID
