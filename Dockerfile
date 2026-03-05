# 1. Pakai mesin dasar Python yang ringan
FROM python:3.10-slim

# 2. Install Node.js (Syarat wajib buat PM2)
RUN apt-get update && apt-get install -y curl
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get install -y nodejs

# 3. Install PM2 secara global
RUN npm install -g pm2

# 4. Pindahkan semua file kodingan dari GitHub ke dalam server
WORKDIR /app
COPY . /app

# 5. Install library Python (requests)
RUN pip install -r requirements.txt

# 6. MANTRA SAKTI: Jalanin 10 bot pakai PM2 supaya server Railway gak mati
CMD ["pm2-runtime", "ecosystem.config.js"]