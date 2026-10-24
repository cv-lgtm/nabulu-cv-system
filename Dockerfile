FROM python:3.12-slim

WORKDIR /app

# Sistem gereksinimleri
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Saat dilimi
ENV TZ=Europe/Istanbul

# Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodları
COPY . .

# Kalıcı veri dizinleri
RUN mkdir -p /app/data /app/storage/cvs

EXPOSE 8088

CMD ["python", "main.py"]
