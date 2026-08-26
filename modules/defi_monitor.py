import aiohttp
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DeFiYieldMonitor:
    def __init__(self):
        self.api_url = "https://yields.llama.fi/pools"

    async def get_top_stablecoin_yields(self, min_tvl_usd: float = 2_000_000, limit: int = 7) -> List[Dict[str, Any]]:
        """DeFiLlama API üzerinden güvenilir ve yüksek TVL'li stablecoin havuzlarını listeler."""
        stable_symbols = ["USDT", "USDC", "USDE", "DAI", "FDUSD", "FRAX"]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, timeout=12) as response:
                    if response.status != 200:
                        logger.error(f"DeFiLlama API hatası: {response.status}")
                        return []
                    
                    data = await response.json()
                    pools = data.get("data", [])

                    filtered_pools = []
                    for p in pools:
                        symbol = p.get("symbol", "").upper()
                        tvl = p.get("tvlUsd", 0)
                        apy = p.get("apy", 0)
                        project = p.get("project", "")
                        chain = p.get("chain", "")

                        # Stablecoin havuzu mu ve TVL yeterli mi?
                        is_stable = any(st in symbol for st in stable_symbols) and ("-" not in symbol or any(st1 in symbol and st2 in symbol for st1 in stable_symbols for st2 in stable_symbols))
                        
                        if is_stable and tvl >= min_tvl_usd and 1.0 <= apy <= 50.0:
                            filtered_pools.append({
                                "project": project.capitalize(),
                                "chain": chain,
                                "symbol": symbol,
                                "tvl_usd": tvl,
                                "apy": apy
                            })

                    # APY'ye göre sırala
                    filtered_pools.sort(key=lambda x: x["apy"], reverse=True)
                    return filtered_pools[:limit]
        except Exception as e:
            logger.error(f"DeFiLlama getiri verisi çekilirken hata: {e}")
            return []

    def format_defi_report(self, pools: List[Dict[str, Any]]) -> str:
        """DeFi getiri verilerini Telegram mesaj formatına dönüştürür."""
        if not pools:
            return "⚠️ Şu anda DeFi getiri verilerine ulaşılamıyor veya uygun havuz bulunamadı."

        lines = [
            "🏦 **DeFi Stablecoin Yüksek Getiri (APY) Havuzları**",
            "*(Minimum \$2M TVL Filtreli - DeFiLlama Verisi)*\n"
        ]

        for idx, p in enumerate(pools, 1):
            lines.append(
                f"{idx}. **{p['project']}** ({p['chain']})\n"
                f"   💵 **Varlık:** `{p['symbol']}`\n"
                f"   📈 **Yıllık Getiri (APY):** `%{p['apy']:.2f}`\n"
                f"   🔒 **TVL:** \${p['tvl_usd']:,.0f}\n"
            )

        lines.append("💡 *Not: Havuz seçerken akıllı kontrat güvenliğini ve protokol geçmişini daima göz önünde bulundurunuz.*")
        return "\n".join(lines)
