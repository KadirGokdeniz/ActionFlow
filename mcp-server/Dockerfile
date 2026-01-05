# ActionFlow MCP Server - SSE tabanlı
FROM python:3.11-slim

WORKDIR /app

# Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyaları
COPY . .

EXPOSE 3000

# FastAPI'yi uvicorn ile başlat
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]
