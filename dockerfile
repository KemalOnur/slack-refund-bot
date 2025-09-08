# Dockerfile
FROM python:3.11-slim

# sistem bağımlılıkları (opsiyonel ama iyi pratik)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# pip gereksinimleri
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# uygulama dosyaları
COPY . /app/

# prod: 0.0.0.0:3000 dinliyoruz (app.py zaten yapıyor)
ENV TZ=Europe/Istanbul

# container içinden çalıştırma
CMD ["python", "app.py"]
