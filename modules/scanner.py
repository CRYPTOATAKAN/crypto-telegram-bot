import asyncio
import time
import pandas as pd
import ta
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from modules.market_data import MarketDataProvider
import config

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Kullanıcının sürekli aynı token bildirimleriyle rahatsız edilmesini önleyen
    akıllı durum takibi ve soğuma (cooldown / deduplication) yöneticisi.
    """
    def __init__(self, cooldown_hours: float = config.ALERT_COOLDOWN_HOURS):
        self.cooldown_seconds = cooldown_hours * 3600
        # {(symbol, signal_id): {"time": float, "price": float, "text": str, "symbol": str, "id": str}}
        self.active_alerts: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def filter_new_signals(self, symbol: str, signals: List[Dict[str, Any]], current_price: float) -> List[Dict[str, Any]]:
        """
        Sinyalleri soğuma süresi ve durum kontrolünden geçirir.
        Yalnızca yeni veya soğuma süresi dolmuş sinyalleri döner.
        """
        now = time.time()
        new_signals = []
        for sig in signals:
            sig_id = sig["id"]
            key = (symbol, sig_id)
            if key in self.active_alerts:
                last_info = self.active_alerts[key]
                time_diff = now - last_info["time"]
                if time_diff < self.cooldown_seconds:
                    logger.debug(f"{symbol} [{sig_id}] uyarısı soğuma süresinde ({time_diff/60:.1f} dk < {self.cooldown_seconds/60:.1f} dk). Engellendi.")
                    continue

            # Yeni veya süresi dolmuş sinyal
            self.active_alerts[key] = {
                "time": now,
                "price": current_price,
                "text": sig["text"],
                "symbol": symbol,
                "id": sig_id,
                "is_early": sig.get("is_early", False)
            }
            new_signals.append(sig)
        return new_signals

    def cleanup_resolved(self, current_active_keys: Set[Tuple[str, str]]):
        """
        Koşulu sona eren sinyalleri aktif listeden temizler.
        Böylece token normalleşip sonradan tekrar sinyal üretirse anında yeni bildirim gider.
        """
        keys_to_remove = [k for k in self.active_alerts if k not in current_active_keys]
        for k in keys_to_remove:
            logger.info(f"{k[0]} [{k[1]}] sinyali çözüldü/sonlandı. Takip listesinden kaldırıldı.")
            del self.active_alerts[k]

    def get_active_alerts_summary(self) -> List[Dict[str, Any]]:
        """Şu an takipte olan aktif sinyalleri ve kalan soğuma sürelerini döner."""
        now = time.time()
        summary = []
        for (symbol, sig_id), data in self.active_alerts.items():
            elapsed_hours = (now - data["time"]) / 3600
            remaining_cooldown = max(0.0, (self.cooldown_seconds - (now - data["time"])) / 3600)
            summary.append({
                "symbol": symbol,
                "id": sig_id,
                "price": data["price"],
                "is_early": data.get("is_early", False),
                "elapsed_hours": elapsed_hours,
                "remaining_cooldown_hours": remaining_cooldown
            })
        return summary


class TechnicalScanner:
    def __init__(self, data_provider: MarketDataProvider):
        self.data_provider = data_provider
        self.alert_manager = AlertManager(cooldown_hours=config.ALERT_COOLDOWN_HOURS)

    def _detect_divergence(self, df: pd.DataFrame, rsi_series: pd.Series) -> List[Dict[str, Any]]:
        """
        Ani çakılış veya yükseliş öncesi en güçlü indikatör olan
        Fiyat - RSI uyuşmazlıklarını (Divergence) tespit eder.
        """
        divergences = []
        if len(df) < 30:
            return divergences

        close = df["close"]
        high = df["high"]
        low = df["low"]

        # 1. Ayı Uyuşmazlığı (Bearish Divergence) - Ani Çakılış Öncesi Erken Uyarı:
        # Fiyat son 3 mumda önceki tepeyi geçerken, RSI önceki tepenin altında kalıyorsa
        prev_window_high = high.iloc[-25:-4]
        if not prev_window_high.empty:
            prev_peak_idx = prev_window_high.idxmax()
            prev_peak_price = high.loc[prev_peak_idx]
            prev_peak_rsi = rsi_series.loc[prev_peak_idx]

            recent_high = high.iloc[-4:].max()
            recent_high_idx = high.iloc[-4:].idxmax()
            recent_rsi = rsi_series.loc[recent_high_idx]

            if (recent_high > prev_peak_price * 1.008) and (recent_rsi < prev_peak_rsi - 3.5) and (recent_rsi > 50):
                divergences.append({
                    "id": "EARLY_BEARISH_DIV",
                    "is_early": True,
                    "text": "🚨 **ERKEN UYARI: Ani Çakılış Riski (Negatif Uyuşmazlık)**\n   Fiyat yeni tepe yaparken momentum zayıflıyor! Ani sert düzeltme / düşüş dalgası başlayabilir."
                })

        # 2. Boğa Uyuşmazlığı (Bullish Divergence) - Ani Sıçrama / Ralli Öncesi Erken Uyarı:
        # Fiyat son 3 mumda önceki dibi delerken, RSI önceki dip seviyesinin üzerinde kalıyorsa
        prev_window_low = low.iloc[-25:-4]
        if not prev_window_low.empty:
            prev_trough_idx = prev_window_low.idxmin()
            prev_trough_price = low.loc[prev_trough_idx]
            prev_trough_rsi = rsi_series.loc[prev_trough_idx]

            recent_low = low.iloc[-4:].min()
            recent_low_idx = low.iloc[-4:].idxmin()
            recent_rsi_low = rsi_series.loc[recent_low_idx]

            if (recent_low < prev_trough_price * 0.992) and (recent_rsi_low > prev_trough_rsi + 3.5) and (recent_rsi_low < 50):
                divergences.append({
                    "id": "EARLY_BULLISH_DIV",
                    "is_early": True,
                    "text": "🚀 **ERKEN UYARI: Ani Sıçrama / Yükseliş (Pozitif Uyuşmazlık)**\n   Fiyat yeni dip yaparken RSI güç topluyor! Ani yukarı tepki / ralli başlayabilir."
                })

        return divergences

    async def analyze_symbol(self, symbol: str, timeframe: str = "4h") -> Optional[Dict[str, Any]]:
        """Bir sembolün teknik indikatörlerini ve erken uyarı modellerini hesaplar."""
        ohlcv = await self.data_provider.get_ohlcv(symbol, timeframe=timeframe, limit=100)
        if not ohlcv or len(ohlcv) < 50:
            return None

        # DataFrame oluşturma
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        close = df["close"]
        open_p = df["open"]
        volume = df["volume"]

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

        # Yapılandırılmış Sinyal Tespiti
        signals: List[Dict[str, Any]] = []

        # 1. RSI Aşırı Uç Sinyalleri
        if current_rsi <= config.RSI_OVERSOLD:
            signals.append({
                "id": "RSI_OVERSOLD",
                "is_early": False,
                "text": f"⚠️ **RSI Aşırı Satım Bölgesinde ({current_rsi:.1f})** - Dip / Tepki Fırsatı"
            })
        elif current_rsi >= config.RSI_OVERBOUGHT:
            signals.append({
                "id": "RSI_OVERBOUGHT",
                "is_early": False,
                "text": f"⚠️ **RSI Aşırı Alım Bölgesinde ({current_rsi:.1f})** - Düzeltme Riski"
            })

        # 2. MACD Kesişim Sinyalleri
        if macd_diff > 0 and macd.macd_diff().iloc[-2] <= 0:
            signals.append({
                "id": "MACD_BULL_CROSS",
                "is_early": False,
                "text": "✨ **MACD Al Sinyali (Kesişim Yukarı)**"
            })
        elif macd_diff < 0 and macd.macd_diff().iloc[-2] >= 0:
            signals.append({
                "id": "MACD_BEAR_CROSS",
                "is_early": False,
                "text": "⚠️ **MACD Sat Sinyali (Kesişim Aşağı)**"
            })

        # 3. ERKEN UYARI MEKANİZMALARI (Pre-Pump / Pre-Dump)
        if config.EARLY_WARNING_ENABLED:
            # A. Uyuşmazlıklar (Divergences)
            divs = self._detect_divergence(df, rsi_series)
            signals.extend(divs)

            # B. Anormal Hacim Patlaması (Volume Spike - Fiyat hareketini önceler)
            vol_sma20 = volume.rolling(20).mean()
            if len(volume) >= 20 and vol_sma20.iloc[-1] > 0:
                cur_vol = volume.iloc[-1]
                avg_vol = vol_sma20.iloc[-1]
                vol_ratio = cur_vol / avg_vol

                if vol_ratio >= config.VOLUME_SPIKE_MULTIPLIER:
                    is_dump = close.iloc[-1] < open_p.iloc[-1]
                    if is_dump:
                        signals.append({
                            "id": "EARLY_VOL_SPIKE_DOWN",
                            "is_early": True,
                            "text": f"⚡ **ERKEN UYARI: Ani Satış Dalgası ({vol_ratio:.1f}x Hacim)**\n   Ortalamanın {vol_ratio:.1f} katı anormal satış hacmi girdi, ani çakılış hızlanabilir!"
                        })
                    else:
                        signals.append({
                            "id": "EARLY_VOL_SPIKE_UP",
                            "is_early": True,
                            "text": f"⚡ **ERKEN UYARI: Ani Alım Dalgası ({vol_ratio:.1f}x Hacim)**\n   Ortalamanın {vol_ratio:.1f} katı anormal alım hacmi girdi, ani yükseliş atağı başlayabilir!"
                        })

            # C. Bollinger Band Daralması (Volatility Squeeze - Sert Patlama Öncesi)
            bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
            mavg = bb.bollinger_mavg().iloc[-1]
            if mavg and mavg > 0:
                bandwidth = (bb.bollinger_hband().iloc[-1] - bb.bollinger_lband().iloc[-1]) / mavg
                if bandwidth <= config.BOLLINGER_SQUEEZE_THRESHOLD:
                    signals.append({
                        "id": "EARLY_BB_SQUEEZE",
                        "is_early": True,
                        "text": f"⚠️ **ERKEN UYARI: Volatilite Sıkışması (Bant: %{bandwidth*100:.1f})**\n   Fiyat aşırı derecede sıkıştı! Saatler içinde ani ve sert bir yön patlaması yaklaşıyor."
                    })

            # D. Vadeli Fonlama Oranı (Funding Rate) Squeeze & Likidasyon Tespiti
            if funding_rate is not None:
                if funding_rate <= -0.0003:  # <= -%0.03
                    signals.append({
                        "id": "EARLY_SHORT_SQUEEZE",
                        "is_early": True,
                        "text": f"⚡ **ERKEN UYARI: Short Squeeze / Ani Patlama Potansiyeli (Fonlama: %{funding_rate*100:.3f})**\n   Vadeli piyasada aşırı short yığılması var! Short tasfiyesiyle sert yukarı patlama gelebilir."
                    })
                elif funding_rate >= 0.0005:  # >= +%0.05
                    signals.append({
                        "id": "EARLY_LONG_LIQUIDATION",
                        "is_early": True,
                        "text": f"🚨 **ERKEN UYARI: Long Tasfiyesi / Ani Çakılış Riski (Fonlama: %{funding_rate*100:.3f})**\n   Vadeli piyasada aşırı kaldıraçlı long yığılması var! Ani çakılış ve uzun pozisyon temizliği gelebilir."
                    })

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
        """Takip listesindeki tüm coinleri paralel ve hızlı bir şekilde asenkron tarar."""
        semaphore = asyncio.Semaphore(10)

        # Vadeli fonlama oranlarını çek
        funding_rates = {}
        try:
            funding_rates = await self.data_provider.get_funding_rates()
        except Exception as e:
            logger.warning(f"Tarama sırasında fonlama oranları alınamadı: {e}")

        async def analyze_with_semaphore(sym: str):
            async with semaphore:
                try:
                    fr = funding_rates.get(sym)
                    return await self.analyze_symbol(sym, timeframe=timeframe, funding_rate=fr)
                except Exception as e:
                    logger.error(f"{sym} analiz edilirken hata: {e}")
                    return None

        tasks = [analyze_with_semaphore(sym) for sym in symbols]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        results = [r for r in raw_results if isinstance(r, dict)]
        return results

    async def scan_for_alerts(self, symbols: List[str]) -> List[str]:
        """
        Yalnızca kritik sinyal üreten coinler için bildirim metinleri hazırlar.
        Tekrarlayan spam uyarıları engeller (AlertManager).
        """
        results = await self.scan_watchlist(symbols, timeframe="4h")
        
        # Aktif koşulları topla ve çözülmüş sinyalleri temizle
        current_active_keys: Set[Tuple[str, str]] = set()
        for res in results:
            for s in res["signals"]:
                current_active_keys.add((res["symbol"], s["id"]))
        self.alert_manager.cleanup_resolved(current_active_keys)

        # Yeni tetiklenen veya soğuma süresi dolmuş sinyalleri filtrele
        alert_messages = []
        for res in results:
            filtered_signals = self.alert_manager.filter_new_signals(
                symbol=res["symbol"],
                signals=res["signals"],
                current_price=res["price"]
            )
            if not filtered_signals:
                continue

            early_signals = [s["text"] for s in filtered_signals if s.get("is_early")]
            standard_signals = [s["text"] for s in filtered_signals if not s.get("is_early")]

            msg_parts = [
                f"🔔 **Piyasa Uyarısı: {res['symbol']} (4S)**",
                f"💵 **Fiyat:** \${res['price']:,.4f}",
                f"📊 **RSI (14):** `{res['rsi']:.1f}` | **Trend:** {res['trend']}\n"
            ]

            if early_signals:
                msg_parts.append("⚡ **ERKEN UYARI (Hareket Öncesi):**")
                msg_parts.extend(early_signals)
                msg_parts.append("")

            if standard_signals:
                if early_signals:
                    msg_parts.append("📌 **Teknik Göstergeler:**")
                msg_parts.extend(standard_signals)

            alert_messages.append("\n".join(msg_parts))

        return alert_messages

