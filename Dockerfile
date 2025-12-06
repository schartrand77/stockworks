FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

WORKDIR $APP_HOME

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash gosu tzdata ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENV DEBIAN_FRONTEND=dialog

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PUID=1000 \
    PGID=1000 \
    UMASK=002 \
    TZ=UTC \
    STOCKWORKS_DATA_DIR=/data \
    STOCKWORKS_DB_FILENAME=app.db

VOLUME ["/data"]

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
