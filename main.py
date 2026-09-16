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
from modules.market_data import MarketDataProvider
from modules.scanner import TechnicalScanner
from modules.risk_calc import RiskCalculator
from modules.defi_monitor import DeFiYieldMonitor

logger = logging.getLogger("CryptoBot")

# Modül Örnekleri
market_data = MarketDataProvider()
scanner = TechnicalScanner(market_data)
risk_calculator = RiskCalculator(total_capital=config.PORTFOLIO_CAPITAL_USDT)
defi_monitor = DeFiYieldMonitor()


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
            InlineKeyboardButton("⚡ Erken Uyarı & Alarmlar", callback_data="btn_alarmlar"),
            InlineKeyboardButton("🏦 DeFi Getirileri", callback_data="btn_defi")
        ],
        [
            InlineKeyboardButton("🎯 Risk Hesaplayıcı", callback_data="btn_risk_info"),
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
        "🤖 **Kripto Analiz & Risk Asistanı** devrede.\n"
        "40+ likit token ve piyasanın en yüksek hacimli çiftleri 7/24 izlenir. "
        "Ani çakılış ve yükselişler **gerçekleşmeden önce** erken uyarılar üretilir ve tekrarlayan spam bildirimler filtrelenir.\n\n"
        "🔹 `/rapor` - Piyasa Özeti, Liderler & Günün En Çok Kazanan/Kaybedenleri\n"
        "🔹 `/tara` - 40+ Token Teknik Analiz & Erken Uyarı Taraması\n"
        "🔹 `/alarmlar` - Aktif Takipteki Sinyaller & Soğuma Durumu\n"
        "🔹 `/risk [Giriş] [Stop] [Hedef]` - Pozisyon Büyüklüğü Hesapla\n"
        "🔹 `/defi` - En Yüksek Stablecoin Faiz Oranları (APY)\n"
        "🔹 `/menu` - Hızlı Buton Menüsü"
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

    # Fiyat verilerini 24s değişime göre sırala
    sorted_tickers = sorted(tickers, key=lambda x: x["change_24h"], reverse=True)
    
    # Lider Coinler (BTC, ETH, SOL, BNB)
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

    # En Çok Yükselenler (Top 4)
    lines.append("\n🚀 **Günün En Çok Kazandıranları (Top Movers):**")
    for t in sorted_tickers[:4]:
        sym = t["symbol"].replace("/USDT", "")
        lines.append(f"🟢 **{sym}:** \${t['price']:,.4f} (`+{t['change_24h']:.2f}%`)")

    # En Çok Düşenler (Top 4)
    lines.append("\n🩸 **Günün En Çok Gerileyenleri:**")
    for t in sorted_tickers[-4:][::-1]:
        sym = t["symbol"].replace("/USDT", "")
        lines.append(f"🔴 **{sym}:** \${t['price']:,.4f} (`{t['change_24h']:.2f}%`)")

    lines.append(f"\n📡 *Toplam {len(tickers)} aktif USDT işlem çifti izleniyor.*")

    await msg.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


@restricted
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Takip listesindeki ve hacimli coinleri teknik göstergeler ve erken uyarılar için tarar."""
    msg = await update.effective_message.reply_text("🔍 *40+ token için grafikler ve erken uyarı modelleri taranıyor...*", parse_mode="Markdown")
    
    symbols = await market_data.get_active_scan_symbols()
    results = await scanner.scan_watchlist(symbols, timeframe="4h")
    if not results:
        await msg.edit_text("⚠️ Tarama verisi alınamadı.", reply_markup=get_main_menu_keyboard())
        return

    # Sinyal üretenler ve üretmeyenleri ayır
    signal_results = [r for r in results if r["signals"]]
    
    # Piyasa Trend İstatistikleri
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

    # Mesaj çok uzunsa kırpma kontrolü (Telegram 4096 char limiti)
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


@restricted
async def defi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """DeFiLlama stablecoin getirilerini listeler."""
    msg = await update.effective_message.reply_text("⏳ *DeFi havuzları sorgulanıyor...*", parse_mode="Markdown")
    pools = await defi_monitor.get_top_stablecoin_yields(min_tvl_usd=2_000_000, limit=6)
    report_text = defi_monitor.format_defi_report(pools)
    await msg.edit_text(report_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


@restricted
async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Kullanım: /risk [Giriş] [Stop] [Hedef (isteğe bağlı)] [Risk Yüzdesi (isteğe bağlı)]
    Örnek: /risk 64000 62500 68000 1.5
    """
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
    elif data == "btn_alarmlar":
        await alarms_command(update, context)
    elif data == "btn_defi":
        await defi_command(update, context)
    elif data == "btn_risk_info":
        await query.message.reply_text(
            "🎯 **Risk Hesaplamak İçin:**\n"
            "`/risk [Giriş_Fiyatı] [Stop_Fiyatı] [Hedef_Fiyat]` şeklinde mesaj yazabilirsiniz.\n\n"
            "Örnek: `/risk 64000 62500 68000`",
            parse_mode="Markdown"
        )
    elif data == "btn_menu":
        await query.message.reply_text("🎛️ **Ana Menü:**", reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")


async def background_scan_job(context: ContextTypes.DEFAULT_TYPE):
    """Belirli aralıklarla piyasayı tarayıp kritik sinyal oluştuğunda otomatik bildirim atar."""
    if config.ALLOWED_TELEGRAM_USER_ID == 0:
        return

    try:
        symbols = await market_data.get_active_scan_symbols()
        alerts = await scanner.scan_for_alerts(symbols)
        if not alerts:
            return

        # Bildirimleri toplu ve temiz şekilde konsolide et
        current_chunk = f"🚨 **Piyasa Radarı: {len(alerts)} Yeni Sinyal/Erken Uyarı!**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for alert_text in alerts:
            if len(current_chunk) + len(alert_text) + 20 > 3800:
                await context.bot.send_message(
                    chat_id=config.ALLOWED_TELEGRAM_USER_ID,
                    text=current_chunk,
                    parse_mode="Markdown"
                )
                current_chunk = ""
            current_chunk += alert_text + "\n\n────────────────\n\n"

        if current_chunk.strip():
            await context.bot.send_message(
                chat_id=config.ALLOWED_TELEGRAM_USER_ID,
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

    # Komut Yönlendiricileri
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("rapor", report_command))
    application.add_handler(CommandHandler("tara", scan_command))
    application.add_handler(CommandHandler("alarmlar", alarms_command))
    application.add_handler(CommandHandler("defi", defi_command))
    application.add_handler(CommandHandler("risk", risk_command))
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # 7/24 Arka Plan Tarama Görevi (Her SCAN_INTERVAL_MINUTES dakikada bir)
    job_queue = application.job_queue
    if job_queue:
        interval_seconds = config.SCAN_INTERVAL_MINUTES * 60
        job_queue.run_repeating(background_scan_job, interval=interval_seconds, first=30)
        logger.info(f"Arka plan teknik tarama görevi kuruldu (Periyot: {config.SCAN_INTERVAL_MINUTES} dakika).")

    # Botu Polling modunda çalıştır
    application.run_polling(drop_pending_updates=True)



if __name__ == "__main__":
    main()
