# 1. Aşama: Python 3.10 tabanlı hafif bir imaj kullanıyoruz
FROM python:3.10-slim

# 2. Aşama: Çalışma dizinini belirliyoruz (Konteyner içinde /app klasörü)
WORKDIR /app

# 3. Aşama: Sistem bağımlılıklarını kuruyoruz
# psycopg2 (Postgres sürücüsü) derlenirken gcc ve libpq-dev'e ihtiyaç duyar.
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 4. Aşama: Bağımlılıkları kopyalayıp kuruyoruz
# Önce sadece requirements.txt'yi kopyalıyoruz (Docker cache avantajı için)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Aşama: Projenin tüm dosyalarını kopyalıyoruz
COPY . .

# 6. Aşama: Uygulamanın dış dünyaya açacağı portu belirtiyoruz
EXPOSE 8000

# 7. Aşama: Uygulamayı uvicorn ile başlatıyoruz
# --host 0.0.0.0 konteynerin dışarıdan erişilebilir olmasını sağlar
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]