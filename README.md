# 🤖 Kripto Portföy & Piyasa Asistanı Telegram Botu

11.000 USDT sermaye yönetimi ve günlük 1–2 saatlik işlem rutini için geliştirilmiş; 7/24 piyasayı tarayan, RSI/Trend sinyalleri üreten, DeFi getiri oranlarını izleyen ve sermaye koruma odaklı pozisyon hesaplayan **Python Telegram Botu**.

Doğrudan **GitHub** ve **Northflank** üzerinde 7/24 kesintisiz (Worker) çalışmak üzere tasarlanmıştır.

---

## 🚀 Özellikler

- **📊 Anlık Piyasa Raporu (`/rapor`):** BTC, ETH, SOL, BNB liderleri, Korku & Açgözlülük Endeksi ve günün en çok kazanan/kaybeden tokenleri.
- **🌐 40+ Likit Token & Dinamik Hacim Taraması:** Piyasanın en likit 40+ tokeni ve Binance'in en yüksek 24s işlem hacmine sahip çiftleri otomatik taranır.
- **⚡ Ani Hareket Öncesi Erken Uyarılar (Pre-Pump & Pre-Dump):**
  - **Uyuşmazlık Tespiti (RSI Divergence):** Fiyat zirve/dip tazelerken RSI'ın ayrışmasıyla ani çakılış ve sıçramaları hareket başlamadan önceden haber verir.
  - **Anormal Hacim Patlaması:** Ortalamanın 2.5 katı hacim girdiğinde ("Volume precedes price") hareket öncesi uyarır.
  - **Bollinger Sıkışması (Volatility Squeeze):** Volatilitenin aşırı daraldığı ve sert patlamanın yaklaştığı anları yakalar.
- **🛡️ Akıllı Spam Önleme & Soğuma (Deduplication / AlertManager):** Aynı token aynı bölgede kaldığı sürece her taramada tekrar bildirim gönderilmez. Sadece yeni durum oluştuğunda veya belirlenen soğuma süresi (örn. 6 saat) dolduğunda haber verir.
- **🔍 4 Saatlik Teknik Tarama (`/tara`):** 40+ tokeni 1-2 saniye içinde paralel tarar, kritik sinyal ve erken uyarı verenleri listeler.
- **🔔 Aktif Takip ve Alarmlar (`/alarmlar`):** Takipte olan aktif sinyalleri ve kalan soğuma sürelerini gösterir.
- **🎯 Risk & Pozisyon Hesaplayıcı (`/risk`):** 11.000 USDT sermayenize ve belirlediğiniz stop mesafesine göre kaç dolarlık ve kaç adet coin almanız gerektiğini hesaplar; sermayenizi korur.
- **🏦 DeFi Yüksek Getiri Havuzları (`/defi`):** DeFiLlama üzerinden \$2M+ TVL'e sahip en yüksek APY veren güvenilir stablecoin havuzlarını listeler.
- **🔒 Kişisel Güvenlik Filtresi:** Bot yalnızca yapılandırılan `ALLOWED_TELEGRAM_USER_ID` sahibine yanıt verir.

---

## 🛠️ Kurulum ve Hazırlık

### 1. Telegram Bot Token ve ID Alma
1. Telegram'da **[@BotFather](https://t.me/BotFather)** botunu açın ve `/newbot` komutunu gönderin.
2. Botunuza bir isim ve kullanıcı adı verin; size verilen **HTTP API Token**'ı kopyalayın.
3. Kendi Telegram ID'nizi öğrenmek için **[@userinfobot](https://t.me/userinfobot)** veya **[@getmyid_bot](https://t.me/getmyid_bot)** botuna mesaj atın ve `Id` numaranızı kopyalayın.

---

## 🌐 Northflank & GitHub Dağıtım Rehberi

### Adım 1: Projeyi GitHub'a Yükleme

Terminalinizde proje dizinine gidin ve GitHub reponuza yükleyin:

```bash
git add .
git commit -m "feat: Genisletilmis 40+ token, erken uyari ve akilli alarm sogutma sistemi"
git push origin main
```

---

### Adım 2: Northflank Üzerinde Canlıya Alma

1. [Northflank](https://northflank.com/) hesabınıza giriş yapın.
2. Bir **Project** oluşturun (veya mevcut projenizi seçin).
3. **"Create Service"** -> **"Deployment Service"** seçeneğine tıklayın.
4. **Source:**
   - **Repository:** GitHub reponuzu seçin.
   - **Branch:** `main`
   - **Build Type:** `Dockerfile` (Otomatik algılanacaktır).
5. **Service Type:**
   - **Deployment Type:** `Worker` (veya Non-HTTP background service seçin).
6. **Environment Variables (Ortam Değişkenleri):**
   `Environment` sekmesinden şu anahtarları ekleyin:
   - `TELEGRAM_BOT_TOKEN`: `@BotFather`'dan aldığınız token.
   - `ALLOWED_TELEGRAM_USER_ID`: Sizin sayısal Telegram kullanıcı ID'niz (Örn: `123456789`).
   - `DYNAMIC_TOP_TOKENS`: `true`
   - `TOP_TOKENS_LIMIT`: `40`
   - `SCAN_INTERVAL_MINUTES`: `15`
   - `ALERT_COOLDOWN_HOURS`: `6.0`
   - `EARLY_WARNING_ENABLED`: `true`
   - `PORTFOLIO_CAPITAL_USDT`: `11000`
   - `DEFAULT_RISK_PERCENT`: `1.5`
7. **Create Service** butonuna basarak dağıtımı başlatın.

> 🎉 **Tebrikler!** Northflank, projenizi derleyip 7/24 arka planda çalıştıracaktır. GitHub'a her yeni commit attığınızda Northflank botunuzu otomatik günceller.

---

## 💻 Yerel Geliştirme ve Test (Localhost)

Botu kendi bilgisayarınızda test etmek isterseniz:

```bash
# 1. Sanal ortam oluşturun ve bağımlılıkları yükleyin
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. .env dosyasını oluşturun
cp .env.example .env
# .env dosyasını açıp TELEGRAM_BOT_TOKEN ve ALLOWED_TELEGRAM_USER_ID girin

# 3. Botu çalıştırın
python main.py
```

---

## 📱 Detaylı Bot Komut Rehberi

| Kategori | Komut | Açıklama & Örnek Kullanım |
| :--- | :--- | :--- |
| **Ana Menü** | `/start` veya `/menu` | İnteraktif butonlu ana kontrol panelini açar. |
| **Rehber** | `/komutlar` veya `/yardim` | Tüm komutların detaylı açıklamalarını ve örneklerini gösterir. |
| **Piyasa** | `/rapor` | BTC, ETH, SOL, BNB liderleri, Korku/Açgözlülük endeksi ve en çok kazanan/kaybedenler. |
| **Tarama** | `/tara` | 40+ token için RSI, MACD, Trend, Sıkışma, Uyuşmazlık ve Vadeli Fonlama taraması. |
| **Teknik Alarm**| `/alarmlar` | Sistemde aktif olan indikatör sinyallerini ve kalan soğuma sürelerini listeler. |
| **Özel Takip** | `/ekle [COIN]` | Kişisel listenize coin ekler (Örn: `/ekle TIA` veya `/ekle SUI`). |
| **Özel Takip** | `/sil [COIN]` | Kişisel listenizden coin çıkarır (Örn: `/sil PEPE`). |
| **Özel Takip** | `/listem` | Sizin tarafınızdan eklenen özel takip listesini görüntüler. |
| **Fiyat Alarmı**| `/alarm [COIN] [FİYAT]` | Özel fiyat hedefi alarmı kurar (Örn: `/alarm BTC 65000` veya `/alarm SOL 135.5`). |
| **Fiyat Alarmı**| `/fiyat_alarmlari` | Bekleyen aktif fiyat hedeflerinizi listeler. |
| **Fiyat Alarmı**| `/alarm_sil [ID]` | İptal etmek istediğiniz fiyat alarmını siler (Örn: `/alarm_sil 1`). |
| **Risk Hesabı** | `/risk [Giriş] [Stop] [Hedef]` | 11.000 USDT sermayeye ve %1.5 riske göre pozisyon büyüklüğü hesaplar. |
| **Trade Kaydı** | `/islem_ac [COIN] [YÖN] [Giriş] [Stop] [Hedef]` | Açtığınız pozisyonu veritabanına kaydeder ve 7/24 Stop/TP takibine alır. |
| **Portföy** | `/pozisyonlar` | Açık işlemlerinizi, anlık fiyatları, canlı Kâr/Zarar ($ ve %) durumunu listeler. |
| **Pozisyon Kapat**| `/kapat [ID] [Çıkış_Fiyatı]` | Açık pozisyonu kapatır ve net kâr/zararı realize eder (Örn: `/kapat 1 67500`). |
| **İşlem Geçmişi**| `/gecmis` | Kapatılmış geçmiş işlemlerinizi ve realize edilen toplam kâr/zararı döner. |
| **DeFi** | `/defi` | \$2M+ TVL'e sahip en yüksek APY veren güvenilir stablecoin havuzlarını listeler. |

