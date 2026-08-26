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
            InlineKeyboardButton("🏦 DeFi Getirileri", callback_data="btn_defi"),
            InlineKeyboardButton("🎯 Risk Hesaplayıcı", callback_data="btn_risk_info")
        ],
        [
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
        "11.000 USDT sermaye yönetimi ve günlük işlem analiziniz için aşağıdaki menüden işlem seçebilir veya komutları kullanabilirsiniz:\n\n"
        "🔹 `/rapor` - Anlık Piyasa Özeti & Korku/Açgözlülük\n"
        "🔹 `/tara` - 4S Grafiklerde RSI & Trend Taraması\n"
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
    """Piyasa genel durumunu ve takip listesindeki fiyatları raporlar."""
    msg = await update.effective_message.reply_text("⏳ *Piyasa verileri toplanıyor...*", parse_mode="Markdown")
    
    overview = await market_data.get_market_overview(config.WATCHLIST)
    fng = overview["fng"]
    tickers = overview["tickers"]

    lines = [
        "📊 **GÜNLÜK PİYASA VE FİYAT RAPORU**\n",
        f"🧭 **Korku & Açgözlülük Endeksi:** `{fng['value']}/100` ({fng['classification']})\n",
        "**Takip Listesi:**"
    ]

    for t in tickers:
        sym = t["symbol"].replace("/USDT", "")
        change_icon = "🟢" if t["change_24h"] >= 0 else "🔴"
        change_sign = "+" if t["change_24h"] >= 0 else ""
        lines.append(
            f"{change_icon} **{sym}:** \${t['price']:,.4f} "
            f"(`{change_sign}{t['change_24h']:.2f}%`)"
        )

    await msg.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


@restricted
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Takip listesindeki coinleri 4 saatlikte teknik olarak tarar."""
    msg = await update.effective_message.reply_text("🔍 *Teknik indikatörler taranıyor (4S grafikler)...*", parse_mode="Markdown")
    
    results = await scanner.scan_watchlist(config.WATCHLIST, timeframe="4h")
    if not results:
        await msg.edit_text("⚠️ Tarama verisi alınamadı.", reply_markup=get_main_menu_keyboard())
        return

    lines = ["🔍 **TEKNİK ANALİZ TARAMA SONUÇLARI (4S)**\n"]
    for r in results:
        sym = r["symbol"].replace("/USDT", "")
        rsi_val = r["rsi"]
        
        # RSI durum ikonu
        if rsi_val <= config.RSI_OVERSOLD:
            rsi_badge = f"`{rsi_val:.1f}` 🟢 (Aşırı Satım / Fırsat)"
        elif rsi_val >= config.RSI_OVERBOUGHT:
            rsi_badge = f"`{rsi_val:.1f}` 🔴 (Aşırı Alım / Risk)"
        else:
            rsi_badge = f"`{rsi_val:.1f}`"

        lines.append(
            f"📌 **{sym}** | Fiyat: \${r['price']:,.2f}\n"
            f"   • RSI (14): {rsi_badge}\n"
            f"   • Trend: {r['trend']}"
        )
        if r["signals"]:
            for sig in r["signals"]:
                lines.append(f"   • {sig}")
        lines.append("")

    await msg.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=get_main_menu_keyboard())


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
        alerts = await scanner.scan_for_alerts(config.WATCHLIST)
        for alert_text in alerts:
            await context.bot.send_message(
                chat_id=config.ALLOWED_TELEGRAM_USER_ID,
                text=alert_text,
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
