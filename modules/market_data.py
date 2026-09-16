import asyncio
import time
import ccxt.async_support as ccxt
import aiohttp
import logging
from typing import Dict, List, Optional, Any
import config

logger = logging.getLogger(__name__)

# Hariç tutulacak stablecoin ve sentetik varlıklar
EXCLUDED_BASE_ASSETS = {
    "USDC", "FDUSD", "TUSD", "BUSD", "DAI", "USDP", "EUR", "AEUR", "PAXG",
    "WBTC", "WETH", "USTC", "EURI", "USD", "USDE"
}


class MarketDataProvider:
    def __init__(self, db=None):
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
        self.db = db
        self._top_volume_cache: List[str] = []
        self._top_volume_cache_time: float = 0.0
        self._cache_ttl_seconds: float = 1800.0  # 30 dakika önbellek

        self._funding_rates_cache: Dict[str, float] = {}
        self._funding_rates_cache_time: float = 0.0
        self._funding_ttl_seconds: float = 600.0  # 10 dakika önbellek

    async def close(self):
        """Bağlantıları kapatır."""
        try:
            await self.exchange.close()
            await self.futures_exchange.close()
        except Exception as e:
            logger.error(f"Exchange bağlantı kapatma hatası: {e}")

    async def get_funding_rates(self) -> Dict[str, float]:
        """Binance Futures üzerinden canlı fonlama oranlarını (Funding Rates) çeker."""
        now = time.time()
        if self._funding_rates_cache and (now - self._funding_rates_cache_time < self._funding_ttl_seconds):
            return self._funding_rates_cache

        rates = {}
        try:
            funding_data = await self.futures_exchange.fetch_funding_rates()
            for key, val in funding_data.items():
                # 'BTC/USDT:USDT' -> 'BTC/USDT'
                norm_sym = key.split(":")[0] if ":" in key else key
                rate = val.get("fundingRate", 0.0)
                if rate is not None:
                    rates[norm_sym] = float(rate)
            self._funding_rates_cache = rates
            self._funding_rates_cache_time = now
            logger.info(f"{len(rates)} adet vadeli fonlama oranı güncellendi.")
        except Exception as e:
            logger.error(f"Fonlama oranları çekilirken hata: {e}")

        return rates

    async def get_top_volume_pairs(self, limit: int = 40) -> List[str]:
        """Binance spot piyasasında 24s hacmi en yüksek USDT çiftlerini dinamik olarak getirir."""
        now = time.time()
        if self._top_volume_cache and (now - self._top_volume_cache_time < self._cache_ttl_seconds):
            return self._top_volume_cache[:limit]

        try:
            tickers = await self.exchange.fetch_tickers()
            usdt_pairs = []
            for symbol, ticker in tickers.items():
                if not symbol.endswith("/USDT"):
                    continue

                base = symbol.split("/")[0]
                # Stablecoinleri ve kaldıraçlı tokenleri (UP/DOWN/BEAR/BULL) filtrele
                if base in EXCLUDED_BASE_ASSETS:
                    continue
                if any(suffix in base for suffix in ("UP", "DOWN", "BULL", "BEAR")):
                    continue

                volume = ticker.get("quoteVolume", 0.0) or 0.0
                usdt_pairs.append((symbol, volume))

            # Hacme göre azalan sırala
            usdt_pairs.sort(key=lambda x: x[1], reverse=True)
            self._top_volume_cache = [p[0] for p in usdt_pairs]
            self._top_volume_cache_time = now
            logger.info(f"Dinamik en yüksek hacimli {len(self._top_volume_cache)} çift güncellendi.")
            return self._top_volume_cache[:limit]
        except Exception as e:
            logger.error(f"Top volume çiftleri çekilirken hata: {e}")
            return config.WATCHLIST[:limit]

    async def get_active_scan_symbols(self) -> List[str]:
        """Tarama için sabit, veritabanı özel listesi ve dinamik coinleri birleştirerek döner."""
        symbols = list(config.WATCHLIST)
        
        # Kullanıcının SQLite'a eklediği özel coinleri dahil et
        if self.db:
            try:
                custom_symbols = self.db.get_custom_watchlist()
                for cs in custom_symbols:
                    if cs not in symbols:
                        symbols.append(cs)
            except Exception as e:
                logger.error(f"DB watchlist okuma hatası: {e}")

        # Dinamik en çok işlem görenleri dahil et
        if config.DYNAMIC_TOP_TOKENS:
            top_pairs = await self.get_top_volume_pairs(limit=config.TOP_TOKENS_LIMIT)
            for sym in top_pairs:
                if sym not in symbols:
                    symbols.append(sym)
        return symbols

    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Belirtilen sembolün anlık fiyat ve 24s değişimini getirir."""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "price": ticker.get("last", 0.0) or 0.0,
                "change_24h": ticker.get("percentage", 0.0) or 0.0,
                "high_24h": ticker.get("high", 0.0) or 0.0,
                "low_24h": ticker.get("low", 0.0) or 0.0,
                "volume_usdt": ticker.get("quoteVolume", 0.0) or 0.0,
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
        """Ana piyasa göstergelerini ve coinleri toplu/asenkron özetler."""
        tickers = []
        try:
            # Tek bir istekte toplu ticker çekmeyi dene
            all_tickers = await self.exchange.fetch_tickers(symbols)
            for sym in symbols:
                if sym in all_tickers:
                    t = all_tickers[sym]
                    tickers.append({
                        "symbol": sym,
                        "price": t.get("last", 0.0) or 0.0,
                        "change_24h": t.get("percentage", 0.0) or 0.0,
                        "high_24h": t.get("high", 0.0) or 0.0,
                        "low_24h": t.get("low", 0.0) or 0.0,
                        "volume_usdt": t.get("quoteVolume", 0.0) or 0.0,
                    })
        except Exception as e:
            logger.warning(f"Toplu ticker çekilemedi, paralel çekiliyor: {e}")
            semaphore = asyncio.Semaphore(10)

            async def fetch_one(s):
                async with semaphore:
                    return await self.get_ticker(s)

            tasks = [fetch_one(s) for s in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            tickers = [r for r in results if isinstance(r, dict)]

        fng = await self.get_fear_and_greed_index()
        return {
            "tickers": tickers,
            "fng": fng
        }

