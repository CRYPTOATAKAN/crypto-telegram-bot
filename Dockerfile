# Hafif ve güvenli Python 3.11 taban imajı
FROM python:3.11-slim

# Çalışma dizinini ayarla
WORKDIR /app

# Sistem bağımlılıklarını güncelle ve gereksizleri temizle
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını kopyala
COPY . .

# Python buffer'ını kapat (logların anında Telegram/Northflank konsoluna düşmesi için)
ENV PYTHONUNBUFFERED=1

# Botu başlat
CMD ["python", "main.py"]
