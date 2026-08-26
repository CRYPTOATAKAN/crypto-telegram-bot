import pandas as pd
import ta
import logging
from typing import Dict, List, Optional, Any
from modules.market_data import MarketDataProvider
import config

logger = logging.getLogger(__name__)

class TechnicalScanner:
    def __init__(self, data_provider: MarketDataProvider):
        self.data_provider = data_provider

    async def analyze_symbol(self, symbol: str, timeframe: str = "4h") -> Optional[Dict[str, Any]]:
        """Bir sembolün teknik indikatörlerini (RSI, EMA, MACD, Trend) hesaplar."""
        ohlcv = await self.data_provider.get_ohlcv(symbol, timeframe=timeframe, limit=100)
        if not ohlcv or len(ohlcv) < 50:
            return None

        # DataFrame oluşturma
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        close = df["close"]

        # İndikatörler
        rsi_series = ta.momentum.RSIIndicator(close=close, window=14).rsi()
        ema_20 = ta.trend.EMAIndicator(close=close, window=20).ema_indicator()
        ema_50 = ta.trend.EMAIndicator(close=close, window=50).ema_indicator()
        ema_200 = ta.trend.EMAIndicator(close=close, window=200).ema_indicator()
        macd = ta.trend.MACD(close=close)

        current_price = close.iloc[-1]
        current_rsi = rsi_series.iloc[-1]
        prev_rsi = rsi_series.iloc[-2]

        current_ema20 = ema_20.iloc[-1] if not ema_20.empty else None
        current_ema50 = ema_50.iloc[-1] if not ema_50.empty else None
        current_ema200 = ema_200.iloc[-1] if not ema_200.empty and not pd.isna(ema_200.iloc[-1]) else None

        macd_line = macd.macd().iloc[-1]
        macd_signal = macd.macd_signal().iloc[-1]
        macd_diff = macd.macd_diff().iloc[-1]

        # Trend Durumu
        trend = "NÖTR"
        if current_ema50 and current_price > current_ema50:
            if current_ema200 and current_price > current_ema200:
                trend = "GÜÇLÜ BOĞA 🟢"
            else:
                trend = "BOĞA 🟢"
        elif current_ema50 and current_price < current_ema50:
            if current_ema200 and current_price < current_ema200:
                trend = "GÜÇLÜ AYI 🔴"
            else:
                trend = "AYI 🔴"

        # Sinyal Tespiti
        signals = []
        if current_rsi <= config.RSI_OVERSOLD:
            signals.append(f"⚠️ **RSI Aşırı Satım Bölgesinde ({current_rsi:.1f})** - Dip / Tepki Fırsatı")
        elif current_rsi >= config.RSI_OVERBOUGHT:
            signals.append(f"⚠️ **RSI Aşırı Alım Bölgesinde ({current_rsi:.1f})** - Düzeltme Riski")

        if macd_diff > 0 and macd.macd_diff().iloc[-2] <= 0:
            signals.append("✨ **MACD Al Sinyali (Kesişim Yukarı)**")
        elif macd_diff < 0 and macd.macd_diff().iloc[-2] >= 0:
            signals.append("⚠️ **MACD Sat Sinyali (Kesişim Aşağı)**")

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "price": current_price,
            "rsi": current_rsi,
            "prev_rsi": prev_rsi,
            "trend": trend,
            "ema50": current_ema50,
            "ema200": current_ema200,
            "signals": signals
        }

    async def scan_watchlist(self, symbols: List[str], timeframe: str = "4h") -> List[Dict[str, Any]]:
        """Takip listesindeki tüm coinleri tarar ve analiz sonuçlarını döner."""
        results = []
        for symbol in symbols:
            analysis = await self.analyze_symbol(symbol, timeframe=timeframe)
            if analysis:
                results.append(analysis)
        return results

    async def scan_for_alerts(self, symbols: List[str]) -> List[str]:
        """Yalnızca kritik sinyal üreten (RSI aşırı uçlar vb.) coinler için bildirim metinleri hazırlar."""
        alerts = []
        results = await self.scan_watchlist(symbols, timeframe="4h")
        for res in results:
            if res["signals"]:
                signal_text = "\n".join(res["signals"])
                alert_msg = (
                    f"🔔 **Piyasa Uyarısı: {res['symbol']} (4S)**\n"
                    f"💵 **Fiyat:** \${res['price']:,.4f}\n"
                    f"📊 **RSI (14):** `{res['rsi']:.1f}`\n"
                    f"📈 **Trend:** {res['trend']}\n\n"
                    f"{signal_text}"
                )
                alerts.append(alert_msg)
        return alerts
