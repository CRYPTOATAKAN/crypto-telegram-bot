import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

import config
from modules.database import DatabaseManager
from modules.market_data import MarketDataProvider
from modules.scanner import TechnicalScanner
from modules.risk_calc import RiskCalculator
from modules.defi_monitor import DeFiYieldMonitor

logger = logging.getLogger("CryptoBot")

# Kalıcı Veritabanı ve Modül Örnekleri
db = DatabaseManager()
market_data = MarketDataProvider(db=db)
scanner = TechnicalScanner(market_data)
risk_calculator = RiskCalculator(total_capital=config.PORTFOLIO_CAPITAL_USDT)
defi_monitor = DeFiYieldMonitor()


def normalize_symbol(user_input: str) -> str:
    """Kullanıcı girdisini Binance uyumlu 'BTC/USDT' formatına dönüştürür."""
    sym = user_input.upper().strip()
    if "/" not in sym:
        sym = f"{sym}/USDT"
    return sym


def restricted(func):
    """Yalnızca izin verilen Telegram kullanıcısının komut çalıştırmasını sağlar."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else 0
        if not config.is_authorized(user_id):
            logger.warning(f"Yetkisiz erişim denemesi: User ID {user_id}")
            if update.effective_message:
                await update.effective_message.reply_text(
                    f"⛔ **Yetkisiz Erişim!**\nSizin Telegram ID'niz: `{user_id}`\n"
                    "Lütfen bu ID'yi botun `.env` veya Northflank yapılandırmasındaki `ALLOWED_TELEGRAM_USER_ID` alanına ekleyin.",
                    parse_mode="Markdown"
                )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def get_main_menu_keyboard():
    """Ana menü interaktif butonlarını oluşturur."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Piyasa Raporu", callback_data="btn_rapor"),
            InlineKeyboardButton("🔍 Teknik Tarama (4S)", callback_data="btn_tara")
        ],
        [
            InlineKeyboardButton("💼 Pozisyonlarım", callback_data="btn_pozisyonlar"),
            InlineKeyboardButton("🎯 Fiyat Alarmları", callback_data="btn_fiyat_alarmlari")
        ],
        [
            InlineKeyboardButton("⚡ Aktif Sinyaller", callback_data="btn_alarmlar"),
            InlineKeyboardButton("🏦 DeFi Getirileri", callback_data="btn_defi")
        ],
        [
            InlineKeyboardButton("📜 Komut Rehberi", callback_data="btn_rehber"),
            InlineKeyboardButton("🔄 Menüyü Yenile", callback_data="btn_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


@restricted
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Başlangıç ve karşılama mesajı."""
    user = update.effective_user
    welcome_text = (
        f"👋 Merhaba **{user.first_name}**!\n\n"
        "🤖 **Kripto Portföy & Piyasa Asistanı** devrede.\n"
        "40+ likit token ve vadeli fonlama oranları (funding rates) 7/24 izlenir. "
        "Ani çakılış ve yükselişler **gerçekleşmeden önce** erken uyarılar üretilir.\n\n"
        "💼 **11.000 USDT** sermayenizi korumak için canlı işlem günlüğü, özel fiyat alarmları ve dinamik takip listesi hazır.\n\n"
        "💡 Tüm komutların detaylı kullanım kılavuzu için `/komutlar` yazabilir veya aşağıdaki menüyü kullanabilirsiniz:"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )


@restricted
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ana buton menüsünü gösterir."""
    await update.message.reply_text(
        "🎛️ **Ana Kontrol Paneli:**",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )


@restricted
async def guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detaylı ve açıklamalı komut rehberini gösterir."""
    guide_text = (
        "📜 **KRİPTO ASİSTAN BOTU - KOMUT REHBERİ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 **PİYASA VE TEKNİK ANALİZ:**\n"
        "• `/rapor` - Lider coinler (BTC, ETH, SOL, BNB), Korku & Açgözlülük endeksi ve günün en çok kazanan/kaybeden tokenleri.\n"
        "• `/tara` - 40+ token için RSI, MACD, Trend ve Erken Uyarı (Divergence, Hacim, Squeeze) taraması.\n"
        "• `/alarmlar` - Teknik indikatör sisteminin takip ettiği aktif sinyaller ve kalan soğuma süreleri.\n\n"
        "🎯 **KİŞİSEL TAKİP LİSTESİ (Kalıcı DB):**\n"
        "• `/ekle [COIN]` - Kişisel takip listenize coin ekler.\n"
        "  *Örnek:* `/ekle TIA` veya `/ekle SUI`\n"
        "• `/sil [COIN]` - Takip listenizden coin çıkarır.\n"
        "  *Örnek:* `/sil PEPE`\n"
        "• `/listem` - Eklediğiniz tüm kişisel coinleri listeler.\n\n"
        "🔔 **ÖZEL FİYAT HEDEF ALARMLARI:**\n"
        "• `/alarm [COIN] [FİYAT]` - Belirlediğiniz fiyata ulaşıldığında anlık sesli bildirim kurar.\n"
        "  *Örnek:* `/alarm BTC 65000` (65.000 yukarı kırılınca)\n"
        "  *Örnek:* `/alarm SOL 135.5` (135.5 aşağı kırılınca)\n"
        "• `/fiyat_alarmlari` - Kurulmuş ve bekleyen aktif fiyat hedeflerini listeler.\n"
        "• `/alarm_sil [ID]` - İstediğiniz fiyat alarmını iptal eder (Örn: `/alarm_sil 1`).\n\n"
        "💼 **11.000 USDT PORTFÖY & TRADE GÜNLÜĞÜ:**\n"
        "• `/risk [Giriş] [Stop] [Hedef] [Risk%]` - Sermaye koruma prensibine göre ideal pozisyon büyüklüğü hesaplar.\n"
        "  *Örnek:* `/risk 64000 62500 68000 1.5`\n"
        "• `/islem_ac [COIN] [YÖN] [Giriş] [Stop] [Hedef]` - Açtığınız pozisyonu veritabanına kaydeder ve 7/24 izlemeye alır.\n"
        "  *Örnek:* `/islem_ac BTC LONG 64000 62500 68000`\n"
        "  *Örnek:* `/islem_ac SOL SHORT 148 152 138`\n"
        "• `/pozisyonlar` - Açık işlemlerinizi, anlık fiyatı, canlı Kâr/Zarar ($ ve %) durumunu listeler.\n"
        "• `/kapat [ID] [Çıkış_Fiyatı (opsiyonel)]` - Açık pozisyonu kapatır ve net kâr/zararı kaydeder.\n"
        "  *Örnek:* `/kapat 1 67500` *(Fiyat belirtmezseniz anlık piyasa fiyatından kapatır)*\n"
        "• `/gecmis` - Başarıyla kapatılmış son işlemlerinizi ve net kâr/zarar toplamını gösterir.\n\n"
        "🏦 **DEFİ & MENÜ:**\n"
        "• `/defi` - \$2M+ TVL'e sahip en yüksek APY veren güvenilir stablecoin havuzları.\n"
        "• `/menu` - Hızlı interaktif buton kontrol panelini açar."
    )
    await update.effective_message.reply_text(guide_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


@restricted
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Piyasa genel durumunu, liderleri ve günün en çok hareket edenlerini raporlar."""
    msg = await update.effective_message.reply_text("⏳ *Piyasa verileri toplanıyor (40+ token)...*", parse_mode="Markdown")
    
    symbols = await market_data.get_active_scan_symbols()
    overview = await market_data.get_market_overview(symbols)
    fng = overview["fng"]
    tickers = overview["tickers"]

    if not tickers:
        await msg.edit_text("⚠️ Piyasa verisi alınamadı.", reply_markup=get_main_menu_keyboard())
        return

    sorted_tickers = sorted(tickers, key=lambda x: x["change_24h"], reverse=True)
    lead_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]
    leads = [t for t in tickers if t["symbol"] in lead_symbols]

    lines = [
        "📊 **GÜNLÜK PİYASA VE FİYAT RAPORU**",
        f"🧭 **Korku & Açgözlülük:** `{fng['value']}/100` ({fng['classification']})\n",
        "🏆 **Piyasa Liderleri:**"
    ]

    for t in leads:
        sym = t["symbol"].replace("/USDT", "")
        icon = "🟢" if t["change_24h"] >= 0 else "🔴"
        sign = "+" if t["change_24h"] >= 0 else ""
        lines.append(f"{icon} **{sym}:** \${t['price']:,.2f} (`{sign}{t['change_24h']:.2f}%`)")

    lines.append("\n🚀 **Günün En Çok Kazandıranları:**")
    for t in sorted_tickers[:4]:
        sym = t["symbol"].replace("/USDT", "")
        lines.append(f"🟢 **{sym}:** \${t['price']:,.4f} (`+{t['change_24h']:.2f}%`)")

    lines.append("\n🩸 **Günün En Çok Gerileyenleri:**")
    for t in sorted_tickers[-4:][::-1]:
        sym = t["symbol"].replace("/USDT", "")
        lines.append(f"🔴 **{sym}:** \${t['price']:,.4f} (`{t['change_24h']:.2f}%`)")

    lines.append(f"\n📡 *Toplam {len(tickers)} aktif USDT işlem çifti izleniyor.*")

    await msg.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


@restricted
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Takip listesindeki ve hacimli coinleri teknik göstergeler ve erken uyarılar için tarar."""
    msg = await update.effective_message.reply_text("🔍 *40+ token için grafikler, erken uyarılar ve vadeli fonlama taranıyor...*", parse_mode="Markdown")
    
    symbols = await market_data.get_active_scan_symbols()
    results = await scanner.scan_watchlist(symbols, timeframe="4h")
    if not results:
        await msg.edit_text("⚠️ Tarama verisi alınamadı.", reply_markup=get_main_menu_keyboard())
        return

    signal_results = [r for r in results if r["signals"]]
    bull_count = sum(1 for r in results if "BOĞA" in r["trend"])
    bear_count = sum(1 for r in results if "AYI" in r["trend"])
    neutral_count = len(results) - (bull_count + bear_count)

    lines = [
        "🔍 **TEKNİK TARAMA VE ERKEN UYARI RAPORU (4S)**",
        f"📊 **Piyasa Nabzı ({len(results)} Token):** 🟢 {bull_count} Boğa | 🔴 {bear_count} Ayı | ⚪ {neutral_count} Nötr\n"
    ]

    if signal_results:
        lines.append(f"🚨 **DİKKAT ÇEKEN VE SİNYAL ÜRETENLER ({len(signal_results)} Token):**\n")
        for r in signal_results:
            sym = r["symbol"].replace("/USDT", "")
            rsi_val = r["rsi"]

            if rsi_val <= config.RSI_OVERSOLD:
                rsi_badge = f"`{rsi_val:.1f}` 🟢 (Aşırı Satım)"
            elif rsi_val >= config.RSI_OVERBOUGHT:
                rsi_badge = f"`{rsi_val:.1f}` 🔴 (Aşırı Alım)"
            else:
                rsi_badge = f"`{rsi_val:.1f}`"

            lines.append(f"📌 **{sym}** | Fiyat: \${r['price']:,.4f} | RSI: {rsi_badge}")
            lines.append(f"   Trend: {r['trend']}")
            for sig in r["signals"]:
                lines.append(f"   • {sig['text']}")
            lines.append("")
    else:
        lines.append("✅ **Şu anda hiçbir tokende aşırı uç veya kritik erken uyarı bulunmuyor.** Piyasa dengeli/nötr seyrediyor.\n")

    full_text = "\n".join(lines)
    if len(full_text) > 3900:
        full_text = full_text[:3850] + "\n\n⚠️ *(Rapor uzunluğu nedeniyle özetlenmiştir.)*"

    await msg.edit_text(full_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


@restricted
async def alarms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aktif sinyalleri ve spam engelleme (soğuma) durumunu gösterir."""
    summary = scanner.alert_manager.get_active_alerts_summary()
    if not summary:
        await update.effective_message.reply_text(
            "🔕 **Aktif Alarm Bulunmuyor**\n\n"
            f"Şu anda takipte olan veya soğuma sürecinde olan bir sinyal yok. "
            f"Kritik sinyal oluştuğunda bot size anında bildirecektir. (Soğuma: {config.ALERT_COOLDOWN_HOURS:.0f} saat)",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
        return

    lines = [
        "🔔 **AKTİF SİNYAL VE SOĞUMA LİSTESİ**",
        f"*(Aynı sinyaller {config.ALERT_COOLDOWN_HOURS:.0f} saat boyunca tekrar iletilmez)*\n"
    ]

    for item in summary:
        sym = item["symbol"].replace("/USDT", "")
        badge = "⚡ Erken Uyarı" if item.get("is_early") else "📌 Teknik Sinyal"
        lines.append(
            f"• **{sym}** - `{item['id']}` ({badge})\n"
            f"  Kayıt Fiyatı: \${item['price']:,.4f} | Kalan Soğuma: `{item['remaining_cooldown_hours']:.1f} saat`"
        )

    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


# --- Kişisel Takip Listesi Komutları ---
@restricted
async def add_watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanım: /ekle [TOKEN] (Örn: /ekle TIA)"""
    args = context.args
    if not args:
        await update.effective_message.reply_text("⚠️ Lütfen eklenecek coini belirtin.\nÖrnek: `/ekle TIA`", parse_mode="Markdown")
        return

    sym = normalize_symbol(args[0])
    added = db.add_watchlist_symbol(sym)
    if added:
        await update.effective_message.reply_text(f"✅ **{sym}** kişisel takip listenize eklendi ve 7/24 izlemeye alındı.", parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(f"ℹ️ **{sym}** zaten takip listenizde mevcut.", parse_mode="Markdown")


@restricted
async def remove_watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanım: /sil [TOKEN] (Örn: /sil PEPE)"""
    args = context.args
    if not args:
        await update.effective_message.reply_text("⚠️ Lütfen silinecek coini belirtin.\nÖrnek: `/sil PEPE`", parse_mode="Markdown")
        return

    sym = normalize_symbol(args[0])
    removed = db.remove_watchlist_symbol(sym)
    if removed:
        await update.effective_message.reply_text(f"🗑️ **{sym}** kişisel takip listenizden çıkarıldı.", parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(f"ℹ️ **{sym}** özel listenizde bulunamadı.", parse_mode="Markdown")


@restricted
async def list_watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının eklediği özel takip listesini görüntüler."""
    custom = db.get_custom_watchlist()
    if not custom:
        await update.effective_message.reply_text(
            "📋 **Özel Takip Listeniz Boş**\n\n"
            "Yeni coin eklemek için: `/ekle TIA` şeklinde komut gönderebilirsiniz.",
            parse_mode="Markdown"
        )
        return

    lines = ["📋 **KİŞİSEL ÖZEL TAKİP LİSTENİZ:**\n"]
    for idx, sym in enumerate(custom, 1):
        lines.append(f"{idx}. **{sym}**")
    lines.append("\n💡 *Bu coinler genel taramaya ve 7/24 erken uyarı radarına otomatik dahil edilir.*")
    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")


# --- Özel Fiyat Alarmları ---
@restricted
async def set_price_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanım: /alarm [TOKEN] [FİYAT] (Örn: /alarm BTC 65000)"""
    args = context.args
    if not args or len(args) < 2:
        await update.effective_message.reply_text(
            "🎯 **Fiyat Hedef Alarmı Kurulumu:**\n\n"
            "Format: `/alarm [COIN] [HEDEF_FİYAT]`\n\n"
            "**Örnekler:**\n"
            "• `/alarm BTC 65000`\n"
            "• `/alarm SOL 135.5`",
            parse_mode="Markdown"
        )
        return

    sym = normalize_symbol(args[0])
    try:
        target_price = float(args[1].replace(",", "."))
    except ValueError:
        await update.effective_message.reply_text("⚠️ Hata: Lütfen geçerli bir sayısal hedef fiyat girin.")
        return

    ticker = await market_data.get_ticker(sym)
    if not ticker or ticker["price"] <= 0:
        await update.effective_message.reply_text(f"⚠️ **{sym}** için anlık fiyat alınamadı. Sembolün doğruluğundan emin olun.")
        return

    cur_price = ticker["price"]
    condition = "ABOVE" if target_price > cur_price else "BELOW"
    cond_text = "üzerine çıktığında 🟢" if condition == "ABOVE" else "altına indiğinde 🔴"

    alert_id = db.add_price_alert(sym, target_price, condition)
    await update.effective_message.reply_text(
        f"🔔 **Fiyat Alarmı Kuruldu! (ID: #{alert_id})**\n\n"
        f"🪙 **Varlık:** `{sym}`\n"
        f"💵 **Anlık Fiyat:** \${cur_price:,.4f}\n"
        f"🎯 **Hedef:** \${target_price:,.4f} ({cond_text})\n\n"
        f"Bot fiyat bu seviyeye ulaştığında anında Telegram'dan size bildirecektir.",
        parse_mode="Markdown"
    )


@restricted
async def list_price_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bekleyen aktif fiyat hedeflerini listeler."""
    alerts = db.get_active_price_alerts()
    if not alerts:
        await update.effective_message.reply_text(
            "🔕 **Aktif Fiyat Alarmı Bulunmuyor**\n\n"
            "Yeni bir fiyat alarmı kurmak için: `/alarm BTC 65000` yazabilirsiniz.",
            parse_mode="Markdown"
        )
        return

    lines = ["🎯 **BEKLEYEN AKTİF FİYAT ALARMLARI:**\n"]
    for a in alerts:
        direction = "Yukarı Kırınca 🟢" if a["condition"] == "ABOVE" else "Aşağı Kırınca 🔴"
        lines.append(
            f"• **ID #{a['id']}** | **{a['symbol']}** ➜ \${a['target_price']:,.4f} ({direction})\n"
            f"  İptal etmek için: `/alarm_sil {a['id']}`"
        )
    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")


@restricted
async def delete_price_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanım: /alarm_sil [ID]"""
    args = context.args
    if not args:
        await update.effective_message.reply_text("⚠️ Lütfen silinecek alarmın ID numarasını girin.\nÖrnek: `/alarm_sil 1`", parse_mode="Markdown")
        return

    try:
        alert_id = int(args[0])
    except ValueError:
        await update.effective_message.reply_text("⚠️ Hata: ID sayısal olmalıdır.")
        return

    deleted = db.delete_price_alert(alert_id)
    if deleted:
        await update.effective_message.reply_text(f"🗑️ Alarm **#{alert_id}** başarıyla iptal edildi.")
    else:
        await update.effective_message.reply_text(f"ℹ️ Alarm **#{alert_id}** bulunamadı.")


# --- Canlı İşlem Günlüğü (Trade Journal & PnL) ---
@restricted
async def open_trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Kullanım: /islem_ac [COIN] [LONG/SHORT] [GİRİŞ] [STOP] [HEDEF(opsiyonel)]
    Örnek: /islem_ac BTC LONG 64000 62500 68000
    """
    args = context.args
    if not args or len(args) < 4:
        await update.effective_message.reply_text(
            "💼 **Canlı Pozisyon Kaydı (Trade Journal):**\n\n"
            "Format: `/islem_ac [COIN] [LONG/SHORT] [Giriş] [Stop] [Hedef (opsiyonel)]`\n\n"
            "**Örnekler:**\n"
            "• `/islem_ac BTC LONG 64000 62500 68000`\n"
            "• `/islem_ac SOL SHORT 148 152 138`",
            parse_mode="Markdown"
        )
        return

    sym = normalize_symbol(args[0])
    direction = args[1].upper().strip()
    if direction not in ("LONG", "SHORT"):
        await update.effective_message.reply_text("⚠️ Yön 'LONG' veya 'SHORT' olmalıdır.")
        return

    try:
        entry = float(args[2].replace(",", "."))
        stop = float(args[3].replace(",", "."))
        target = float(args[4].replace(",", ".")) if len(args) >= 5 else None

        # Risk hesabı (11.000 USDT sermaye ve %1.5 varsayılan risk)
        calc = risk_calculator.calculate_position(
            entry_price=entry,
            stop_price=stop,
            risk_percent=config.DEFAULT_RISK_PERCENT,
            target_price=target
        )

        trade_id = db.open_trade(
            symbol=sym,
            direction=direction,
            entry_price=entry,
            stop_price=stop,
            target_price=target,
            position_size_usd=calc["position_size_usd"],
            coin_amount=calc["coin_amount"],
            risk_usd=calc["risk_amount_usd"]
        )

        tp_text = f"\${target:,.4f}" if target else "Belirlenmedi"
        await update.effective_message.reply_text(
            f"✅ **Pozisyon Kaydedildi ve Takibe Alındı! (ID: #{trade_id})**\n\n"
            f"🪙 **İşlem:** `{sym}` ({direction})\n"
            f"📍 **Giriş:** \${entry:,.4f}\n"
            f"🛑 **Stop-Loss:** \${stop:,.4f} (%{calc['stop_distance_pct']:.2f})\n"
            f"🎯 **Hedef (TP):** {tp_text}\n"
            f"💰 **Pozisyon Büyüklüğü:** \${calc['position_size_usd']:,.2f} (`{calc['coin_amount']:.4f}` adet)\n"
            f"🛡️ **Riske Edilen:** \${calc['risk_amount_usd']:,.2f} (%{config.DEFAULT_RISK_PERCENT:.1f})\n\n"
            f"Bot Stop ve Hedef seviyelerini 7/24 izleyecek ve tetiklendiğinde sizi uyaracaktır.\n"
            f"Pozisyonları görmek için: `/pozisyonlar`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.effective_message.reply_text(f"⚠️ Hata: {e}")


@restricted
async def list_positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Açık pozisyonları ve canlı Kâr/Zarar (PnL) durumunu gösterir."""
    trades = db.get_open_trades()
    if not trades:
        await update.effective_message.reply_text(
            "💼 **Açık Pozisyon Bulunmuyor**\n\n"
            "Yeni bir işlem kaydetmek için:\n`/islem_ac BTC LONG 64000 62500 68000` yazabilirsiniz.",
            parse_mode="Markdown"
        )
        return

    msg = await update.effective_message.reply_text("⏳ *Açık pozisyonların anlık fiyatları çekiliyor...*", parse_mode="Markdown")
    lines = ["💼 **CANLI AÇIK POZİSYONLAR (11.000 USDT Sermaye Takibi)**\n"]

    total_floating_pnl = 0.0
    for t in trades:
        sym = t["symbol"]
        ticker = await market_data.get_ticker(sym)
        cur_price = ticker["price"] if ticker else t["entry_price"]

        entry = t["entry_price"]
        size_usd = t["position_size_usd"]
        direction = t["direction"]

        if direction == "LONG":
            pnl_pct = (cur_price - entry) / entry
        else:
            pnl_pct = (entry - cur_price) / entry
        pnl_usd = size_usd * pnl_pct
        total_floating_pnl += pnl_usd

        pnl_icon = "🟢" if pnl_usd >= 0 else "🔴"
        pnl_sign = "+" if pnl_usd >= 0 else ""

        stop_dist = abs(cur_price - t["stop_price"]) / cur_price * 100
        tp_info = f"Hedef: \${t['target_price']:,.2f}" if t.get("target_price") else "Hedefsiz"

        lines.append(
            f"📌 **ID #{t['id']} | {sym} ({direction})**\n"
            f"   • Giriş: \${entry:,.4f} | Anlık: \${cur_price:,.4f}\n"
            f"   • Kâr/Zarar: {pnl_icon} `{pnl_sign}\${pnl_usd:,.2f}` (`{pnl_sign}{pnl_pct*100:.2f}%`)\n"
            f"   • Stop: \${t['stop_price']:,.4f} (%{stop_dist:.1f} mesafe) | {tp_info}\n"
            f"   • Kapatmak için: `/kapat {t['id']}`\n"
        )

    tot_icon = "🟢" if total_floating_pnl >= 0 else "🔴"
    tot_sign = "+" if total_floating_pnl >= 0 else ""
    lines.append(f"━━━━━━━━━━━━━━━━━━━━\n💵 **Toplam Açık PnL:** {tot_icon} `{tot_sign}\${total_floating_pnl:,.2f}`")

    await msg.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


@restricted
async def close_trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanım: /kapat [İŞLEM_ID] [ÇIKIŞ_FİYATI(opsiyonel)]"""
    args = context.args
    if not args:
        await update.effective_message.reply_text("⚠️ Lütfen kapatılacak işlem ID'sini belirtin.\nÖrnek: `/kapat 1`", parse_mode="Markdown")
        return

    try:
        trade_id = int(args[0])
    except ValueError:
        await update.effective_message.reply_text("⚠️ Hata: İşlem ID sayısal olmalıdır.")
        return

    # Çıkış fiyatı girilmediyse canlı fiyatı çek
    exit_price = None
    if len(args) >= 2:
        try:
            exit_price = float(args[1].replace(",", "."))
        except ValueError:
            pass

    if exit_price is None:
        open_trades = db.get_open_trades()
        target_trade = next((t for t in open_trades if t["id"] == trade_id), None)
        if not target_trade:
            await update.effective_message.reply_text(f"ℹ️ ID **#{trade_id}** ile açık pozisyon bulunamadı.")
            return

        ticker = await market_data.get_ticker(target_trade["symbol"])
        exit_price = ticker["price"] if ticker else target_trade["entry_price"]

    closed_trade = db.close_trade(trade_id, exit_price)
    if not closed_trade:
        await update.effective_message.reply_text(f"ℹ️ İşlem kapatılamadı. ID **#{trade_id}** zaten kapalı olabilir.")
        return

    pnl_usd = closed_trade["pnl_usd"]
    pnl_pct = closed_trade["pnl_pct"]
    pnl_icon = "🟢" if pnl_usd >= 0 else "🔴"
    pnl_sign = "+" if pnl_usd >= 0 else ""

    await update.effective_message.reply_text(
        f"🏁 **İşlem Kapatıldı ve Arşivlendi! (ID: #{trade_id})**\n\n"
        f"🪙 **Varlık:** `{closed_trade['symbol']}` ({closed_trade['direction']})\n"
        f"📍 **Giriş:** \${closed_trade['entry_price']:,.4f}\n"
        f"🚪 **Çıkış:** \${exit_price:,.4f}\n"
        f"⚖️ **Net Gerçekleşen Kâr/Zarar:** {pnl_icon} **{pnl_sign}\${pnl_usd:,.2f}** (`{pnl_sign}{pnl_pct:.2f}%`)",
        parse_mode="Markdown"
    )


@restricted
async def trade_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Geçmiş kapatılmış işlemleri listeler."""
    history = db.get_trade_history(limit=8)
    if not history:
        await update.effective_message.reply_text("📜 Henüz kapatılmış geçmiş işlem kaydı yok.")
        return

    lines = ["📜 **GEÇMİŞ KAPATILMIŞ İŞLEMLER:**\n"]
    net_pnl = sum(h.get("pnl_usd", 0.0) or 0.0 for h in history)

    for h in history:
        pnl_usd = h.get("pnl_usd", 0.0) or 0.0
        icon = "🟢" if pnl_usd >= 0 else "🔴"
        sign = "+" if pnl_usd >= 0 else ""
        lines.append(
            f"• **#{h['id']} {h['symbol']} ({h['direction']})** | Çıkış: \${h['exit_price']:,.4f}\n"
            f"  PnL: {icon} `{sign}\${pnl_usd:,.2f}` | Kapanış: {h['closed_at']}"
        )

    net_icon = "🟢" if net_pnl >= 0 else "🔴"
    net_sign = "+" if net_pnl >= 0 else ""
    lines.append(f"\n━━━━━━━━━━━━━━━━━━━━\n💰 **Geçmiş Toplam Realize PnL:** {net_icon} `{net_sign}\${net_pnl:,.2f}`")

    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")


# --- Mevcut Diğer Komutlar ---
@restricted
async def defi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """DeFiLlama stablecoin getirilerini listeler."""
    msg = await update.effective_message.reply_text("⏳ *DeFi havuzları sorgulanıyor...*", parse_mode="Markdown")
    pools = await defi_monitor.get_top_stablecoin_yields(min_tvl_usd=2_000_000, limit=6)
    report_text = defi_monitor.format_defi_report(pools)
    await msg.edit_text(report_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


@restricted
async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanım: /risk [Giriş] [Stop] [Hedef (isteğe bağlı)] [Risk Yüzdesi (isteğe bağlı)]"""
    args = context.args
    if not args or len(args) < 2:
        help_text = (
            "🎯 **Risk & Pozisyon Hesaplayıcı Kullanımı:**\n\n"
            "Format: `/risk [Giriş] [Stop] [Hedef (opsiyonel)] [Risk % (opsiyonel)]`\n\n"
            "**Örnekler:**\n"
            "• `/risk 64000 62500`\n"
            "• `/risk 64000 62500 68000` *(Hedef kâr seviyesi ile)*\n"
            "• `/risk 3200 3100 3500 2.0` *(%2 risk ile)*"
        )
        await update.effective_message.reply_text(help_text, parse_mode="Markdown")
        return

    try:
        entry = float(args[0].replace(",", "."))
        stop = float(args[1].replace(",", "."))
        target = float(args[2].replace(",", ".")) if len(args) >= 3 else None
        risk_pct = float(args[3].replace(",", ".")) if len(args) >= 4 else config.DEFAULT_RISK_PERCENT

        calc_res = risk_calculator.calculate_position(
            entry_price=entry,
            stop_price=stop,
            risk_percent=risk_pct,
            target_price=target
        )
        report = risk_calculator.format_report(calc_res)
        await update.effective_message.reply_text(report, parse_mode="Markdown")
    except ValueError as e:
        await update.effective_message.reply_text(f"⚠️ Hata: Lütfen geçerli sayısal değerler girin. ({e})")


async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İnteraktif buton tıklamalarını yönetir."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "btn_rapor":
        await report_command(update, context)
    elif data == "btn_tara":
        await scan_command(update, context)
    elif data == "btn_pozisyonlar":
        await list_positions_command(update, context)
    elif data == "btn_fiyat_alarmlari":
        await list_price_alerts_command(update, context)
    elif data == "btn_alarmlar":
        await alarms_command(update, context)
    elif data == "btn_defi":
        await defi_command(update, context)
    elif data == "btn_rehber":
        await guide_command(update, context)
    elif data == "btn_risk_info":
        await query.message.reply_text(
            "🎯 **Risk Hesaplamak İçin:**\n"
            "`/risk [Giriş_Fiyatı] [Stop_Fiyatı] [Hedef_Fiyat]` şeklinde mesaj yazabilirsiniz.\n\n"
            "Örnek: `/risk 64000 62500 68000`",
            parse_mode="Markdown"
        )
    elif data == "btn_menu":
        await query.message.reply_text("🎛️ **Ana Menü:**", reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")


# --- 7/24 Arka Plan Tarama ve Alarm Kontrol Görevi ---
async def background_scan_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Belirli aralıklarla:
    1. Piyasa teknik indikatör ve erken uyarı sinyallerini tarar.
    2. Özel hedef fiyat alarmlarını kontrol eder.
    3. Açık pozisyonların Stop veya TP seviyelerini denetler.
    """
    if config.ALLOWED_TELEGRAM_USER_ID == 0:
        return

    chat_id = config.ALLOWED_TELEGRAM_USER_ID

    # 1. Özel Fiyat Alarmlarını Kontrol Et
    try:
        active_price_alerts = db.get_active_price_alerts()
        for pa in active_price_alerts:
            sym = pa["symbol"]
            target = pa["target_price"]
            cond = pa["condition"]

            ticker = await market_data.get_ticker(sym)
            if not ticker or ticker["price"] <= 0:
                continue

            cur_price = ticker["price"]
            triggered = False
            if cond == "ABOVE" and cur_price >= target:
                triggered = True
            elif cond == "BELOW" and cur_price <= target:
                triggered = True

            if triggered:
                db.mark_alert_triggered(pa["id"])
                icon = "🟢" if cond == "ABOVE" else "🔴"
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🎯 **FİYAT HEDEF ALARMI TETİKLENDİ!** {icon}\n\n"
                        f"🪙 **Varlık:** `{sym}`\n"
                        f"🎯 **Hedef Fiyat:** \${target:,.4f}\n"
                        f"💵 **Anlık Fiyat:** \${cur_price:,.4f}\n\n"
                        f"Alarm **#{pa['id']}** başarıyla tamamlandı."
                    ),
                    parse_mode="Markdown"
                )
    except Exception as e:
        logger.error(f"Fiyat alarm kontrol hatası: {e}")

    # 2. Açık İşlemlerin Stop / TP Kontrolü
    try:
        open_trades = db.get_open_trades()
        for t in open_trades:
            sym = t["symbol"]
            ticker = await market_data.get_ticker(sym)
            if not ticker or ticker["price"] <= 0:
                continue

            cur_p = ticker["price"]
            stop_p = t["stop_price"]
            tp_p = t.get("target_price")
            direction = t["direction"]

            # Stop kontrolü
            stop_hit = (cur_p <= stop_p) if direction == "LONG" else (cur_p >= stop_p)
            if stop_hit:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🛑 **DİKKAT: STOP-LOSS SEVİYESİNE ULAŞILDI!**\n\n"
                        f"İşlem **#{t['id']}** ({sym} {direction})\n"
                        f"📍 Giriş: \${t['entry_price']:,.4f}\n"
                        f"🛑 Stop: \${stop_p:,.4f}\n"
                        f"💵 Anlık Fiyat: \${cur_p:,.4f}\n\n"
                        f"Sermayenizi korumak için işlemi kapatabilirsiniz:\n`/kapat {t['id']}`"
                    ),
                    parse_mode="Markdown"
                )

            # TP kontrolü
            if tp_p:
                tp_hit = (cur_p >= tp_p) if direction == "LONG" else (cur_p <= tp_p)
                if tp_hit:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"🎯 **TEBRİKLER: KÂR AL (TP) HEDEFİNE ULAŞILDI!**\n\n"
                            f"İşlem **#{t['id']}** ({sym} {direction})\n"
                            f"📍 Giriş: \${t['entry_price']:,.4f}\n"
                            f"🎯 Hedef: \${tp_p:,.4f}\n"
                            f"💵 Anlık Fiyat: \${cur_p:,.4f}\n\n"
                            f"Kârı realize edip işlemi kapatmak için:\n`/kapat {t['id']}`"
                        ),
                        parse_mode="Markdown"
                    )
    except Exception as e:
        logger.error(f"Pozisyon stop/tp kontrol hatası: {e}")

    # 3. Teknik Tarama & Erken Uyarı Bildirimleri
    try:
        symbols = await market_data.get_active_scan_symbols()
        alerts = await scanner.scan_for_alerts(symbols)
        if not alerts:
            return

        current_chunk = f"🚨 **Piyasa Radarı: {len(alerts)} Yeni Sinyal/Erken Uyarı!**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for alert_text in alerts:
            if len(current_chunk) + len(alert_text) + 20 > 3800:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=current_chunk,
                    parse_mode="Markdown"
                )
                current_chunk = ""
            current_chunk += alert_text + "\n\n────────────────\n\n"

        if current_chunk.strip():
            await context.bot.send_message(
                chat_id=chat_id,
                text=current_chunk,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Arka plan tarama hatası: {e}")


def main():
    """Bot uygulamasını başlatır."""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("HATA: TELEGRAM_BOT_TOKEN ortam değişkeni bulunamadı! Lütfen .env dosyasını kontrol edin.")
        print("❌ Lütfen .env dosyasına veya Northflank Environment Variables paneline TELEGRAM_BOT_TOKEN ekleyin.")
        return

    logger.info("Kripto Asistan Telegram Botu başlatılıyor...")

    application = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Temel Komutlar
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("komutlar", guide_command))
    application.add_handler(CommandHandler("yardim", guide_command))
    application.add_handler(CommandHandler("rapor", report_command))
    application.add_handler(CommandHandler("tara", scan_command))
    application.add_handler(CommandHandler("alarmlar", alarms_command))
    application.add_handler(CommandHandler("defi", defi_command))
    application.add_handler(CommandHandler("risk", risk_command))

    # Kişisel Takip Listesi Komutları
    application.add_handler(CommandHandler("ekle", add_watchlist_command))
    application.add_handler(CommandHandler("sil", remove_watchlist_command))
    application.add_handler(CommandHandler("listem", list_watchlist_command))

    # Fiyat Hedef Alarmları Komutları
    application.add_handler(CommandHandler("alarm", set_price_alert_command))
    application.add_handler(CommandHandler("fiyat_alarmlari", list_price_alerts_command))
    application.add_handler(CommandHandler("alarm_sil", delete_price_alert_command))

    # Trade Journal & Portföy Komutları
    application.add_handler(CommandHandler("islem_ac", open_trade_command))
    application.add_handler(CommandHandler("pozisyonlar", list_positions_command))
    application.add_handler(CommandHandler("kapat", close_trade_command))
    application.add_handler(CommandHandler("gecmis", trade_history_command))

    # Buton Callback Yönetimi
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # 7/24 Arka Plan Tarama Görevi
    job_queue = application.job_queue
    if job_queue:
        interval_seconds = config.SCAN_INTERVAL_MINUTES * 60
        job_queue.run_repeating(background_scan_job, interval=interval_seconds, first=30)
        logger.info(f"Arka plan teknik tarama görevi kuruldu (Periyot: {config.SCAN_INTERVAL_MINUTES} dakika).")

    # Botu Polling modunda çalıştır
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

