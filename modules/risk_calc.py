from typing import Dict, Any, Optional
import config

class RiskCalculator:
    def __init__(self, total_capital: float = config.PORTFOLIO_CAPITAL_USDT):
        self.total_capital = total_capital

    def calculate_position(
        self,
        entry_price: float,
        stop_price: float,
        risk_percent: float = config.DEFAULT_RISK_PERCENT,
        target_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Sermaye koruma prensibine göre pozisyon büyüklüğü ve risk metriklerini hesaplar.
        """
        if entry_price <= 0 or stop_price <= 0:
            raise ValueError("Fiyatlar 0'dan büyük olmalıdır.")

        is_long = entry_price > stop_price
        direction = "LONG 📈" if is_long else "SHORT 📉"

        # Stop mesafesi yüzdesi
        stop_distance_pct = abs(entry_price - stop_price) / entry_price * 100

        # Riske atılan toplam dolar miktarı ($11.000 için örn %1.5 = $165)
        risk_amount_usd = self.total_capital * (risk_percent / 100)

        # Pozisyon Büyüklüğü ($) = Risk Miktarı / Stop Yüzdesi
        position_size_usd = risk_amount_usd / (stop_distance_pct / 100)

        # Alınacak/Satılacak Coin Adedi
        coin_amount = position_size_usd / entry_price

        # Gerekli Kaldıraç / Sermaye Oranı
        leverage_ratio = position_size_usd / self.total_capital

        # Risk / Ödül Oranı (R:R)
        rr_ratio = None
        target_profit_usd = None
        if target_price and target_price > 0:
            target_distance_pct = abs(target_price - entry_price) / entry_price * 100
            rr_ratio = target_distance_pct / stop_distance_pct if stop_distance_pct > 0 else 0
            target_profit_usd = position_size_usd * (target_distance_pct / 100)

        return {
            "direction": direction,
            "total_capital": self.total_capital,
            "risk_percent": risk_percent,
            "risk_amount_usd": risk_amount_usd,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "stop_distance_pct": stop_distance_pct,
            "position_size_usd": position_size_usd,
            "coin_amount": coin_amount,
            "leverage_ratio": leverage_ratio,
            "target_price": target_price,
            "target_profit_usd": target_profit_usd,
            "rr_ratio": rr_ratio
        }

    def format_report(self, res: Dict[str, Any]) -> str:
        """Hesaplama sonucunu Telegram mesaj formatına dönüştürür."""
        lines = [
            f"🎯 **Pozisyon & Risk Planlaması ({res['direction']})**\n",
            f"💼 **Portföy Sermayesi:** \${res['total_capital']:,.2f}",
            f"🛡️ **İşlem Başına Risk:** %{res['risk_percent']:.1f} (\${res['risk_amount_usd']:,.2f})\n",
            f"📍 **Giriş Seviyesi:** \${res['entry_price']:,.4f}",
            f"🛑 **Stop-Loss:** \${res['stop_price']:,.4f} (%{res['stop_distance_pct']:.2f} Mesafe)\n",
            f"💰 **Açılması Gereken Pozisyon:** \${res['position_size_usd']:,.2f}",
            f"🪙 **İşlem Adedi:** `{res['coin_amount']:.4f}` Adet",
        ]

        if res["leverage_ratio"] <= 1.0:
            lines.append(f"📊 **Kaldıraç Önerisi:** Spot / 1x (Sermayenizin %{res['leverage_ratio']*100:.1f}'i)")
        elif res["leverage_ratio"] <= 3.0:
            lines.append(f"📊 **Kaldıraç Önerisi:** {res['leverage_ratio']:.1f}x İzole Kaldıraç")
        else:
            lines.append(f"⚠️ **Kaldıraç Uyarısı:** {res['leverage_ratio']:.1f}x gerekir (Stop mesafesi çok dar veya risk yüksek!)")

        if res["rr_ratio"] is not None:
            lines.append(f"\n🎯 **Hedef (TP):** \${res['target_price']:,.4f}")
            lines.append(f"💵 **Beklenen Kâr:** +\${res['target_profit_usd']:,.2f}")
            rr_status = "Mükemmel 🟢" if res["rr_ratio"] >= 2.0 else "Düşük/Orta 🟡"
            lines.append(f"⚖️ **Risk/Ödül (R:R):** 1 : {res['rr_ratio']:.2f} ({rr_status})")

        return "\n".join(lines)
