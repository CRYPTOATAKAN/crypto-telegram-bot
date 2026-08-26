import ccxt.async_support as ccxt
import aiohttp
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class MarketDataProvider:
    def __init__(self):
        # Halka açık REST API bağlantısı (API anahtarı gerekmez)
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })
        self.futures_exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            }
        })

    async def close(self):
        """Bağlantıları kapatır."""
        try:
            await self.exchange.close()
            await self.futures_exchange.close()
        except Exception as e:
            logger.error(f"Exchange bağlantı kapatma hatası: {e}")

    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Belirtilen sembolün anlık fiyat ve 24s değişimini getirir."""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "price": ticker.get("last", 0.0),
                "change_24h": ticker.get("percentage", 0.0),
                "high_24h": ticker.get("high", 0.0),
                "low_24h": ticker.get("low", 0.0),
                "volume_usdt": ticker.get("quoteVolume", 0.0),
            }
        except Exception as e:
            logger.error(f"{symbol} ticker çekilirken hata: {e}")
            return None

    async def get_ohlcv(self, symbol: str, timeframe: str = "4h", limit: int = 100) -> List[List[Any]]:
        """Teknik analiz için mum verilerini (Open, High, Low, Close, Volume) çeker."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            return ohlcv
        except Exception as e:
            logger.error(f"{symbol} OHLCV ({timeframe}) çekilirken hata: {e}")
            return []

    async def get_fear_and_greed_index(self) -> Dict[str, Any]:
        """Korku ve Açgözlülük Endeksi verisini çeker."""
        url = "https://api.alternative.me/fng/?limit=1"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        item = data.get("data", [])[0]
                        return {
                            "value": int(item.get("value", 50)),
                            "classification": item.get("value_classification", "Neutral")
                        }
        except Exception as e:
            logger.error(f"Fear & Greed çekilirken hata: {e}")
        return {"value": 50, "classification": "Bilinmiyor"}

    async def get_market_overview(self, symbols: List[str]) -> Dict[str, Any]:
        """Ana piyasa göstergelerini ve takip listesindeki coinleri özetler."""
        tickers = []
        for sym in symbols:
            t = await self.get_ticker(sym)
            if t:
                tickers.append(t)

        fng = await self.get_fear_and_greed_index()
        return {
            "tickers": tickers,
            "fng": fng
        }
