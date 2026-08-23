FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .
COPY entrypoint.sh .
COPY config.json /app/defaults/config.json
COPY message.txt /app/defaults/message.txt
RUN chmod +x /app/entrypoint.sh && mkdir -p /data
VOLUME ["/data"]
ENTRYPOINT ["/app/entrypoint.sh"]
