# 🤖 Kripto Portföy & Piyasa Asistanı Telegram Botu

11.000 USDT sermaye yönetimi ve günlük 1–2 saatlik işlem rutini için geliştirilmiş; 7/24 piyasayı tarayan, RSI/Trend sinyalleri üreten, DeFi getiri oranlarını izleyen ve sermaye koruma odaklı pozisyon hesaplayan **Python Telegram Botu**.

Doğrudan **GitHub** ve **Northflank** üzerinde 7/24 kesintisiz (Worker) çalışmak üzere tasarlanmıştır.

---

## 🚀 Özellikler

- **📊 Anlık Piyasa Raporu (`/rapor`):** BTC, ETH, SOL ve takip listesindeki coinlerin anlık fiyatları, 24 saatlik değişimleri ve Korku & Açgözlülük Endeksi.
- **🔍 4 Saatlik Teknik Tarama (`/tara`):** Takip listesindeki coinlerin RSI(14), EMA50/200 trend durumları ve MACD kesişimleri.
- **🔔 7/24 Otomatik Sinyal Bildirimi:** RSI aşırı satım (<30) veya aşırı alım (>70) bölgelerine ulaştığında Telegram'a otomatik bildirim iletir.
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
cd /Users/macbook/.gemini/antigravity/scratch/crypto-telegram-bot

# Git başlatın
git init
git add .
git commit -m "feat: Kripto Telegram Asistan Botu ilk surum"

# GitHub reponuzu bağlayın ve gönderin
git branch -M main
git remote add origin https://github.com/KULLANICI_ADINIZ/REPO_ADINIZ.git
git push -u origin main
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
   - `PORTFOLIO_CAPITAL_USDT`: `11000`
   - `DEFAULT_RISK_PERCENT`: `1.5`
   - `SCAN_INTERVAL_MINUTES`: `30`
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

## 📱 Bot Komut Rehberi

| Komut | Açıklama |
| :--- | :--- |
| `/start` veya `/menu` | İnteraktif butonlu ana menüyü açar. |
| `/rapor` | BTC/ETH/SOL fiyatları ve Korku/Açgözlülük endeksini getirir. |
| `/tara` | 4 saatlik grafiklerde RSI, MACD ve Trend durumunu listeler. |
| `/risk 64000 62500 68000` | Giriş: 64.000, Stop: 62.500, Hedef: 68.000 için ideal pozisyon büyüklüğünü hesaplar. |
| `/defi` | \$2M+ TVL'e sahip en yüksek getirili stablecoin havuzlarını listeler. |
