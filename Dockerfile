from python:3.9-slim

# installing chromium and driver:

RUN apt-get update && apt-get install -y \
    chromium-driver \
    chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# installing dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

#setting environment 

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Running stage

CMD gunicorn --workers 1 --timeout 120 --bind 0.0.0.0:$PORT app:app
