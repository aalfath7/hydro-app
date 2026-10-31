FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Pustaka yang dibutuhkan WeasyPrint untuk membuat PDF.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --system --uid 10001 --no-create-home hydro \
    && mkdir -p /data/media \
    && chown -R hydro /data/media

ENV DJANGO_MEDIA_ROOT=/data/media
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD ["python", "healthcheck.py"]
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-"]
