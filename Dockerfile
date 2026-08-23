FROM python:3.11-slim

# Installer uniquement ce qui est utile pour Flask + Gunicorn + Crypto
RUN apt-get update && apt-get install -y \
    build-essential \
    libasound2 \
    --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
WORKDIR /app
COPY . .

# Commande de lancement
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "1", "main:app", "--timeout", "900"]
