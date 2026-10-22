FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

# WITH_AUTH=true : installe aussi auth-client (production, AUTH_ENABLED=true)
ARG WITH_AUTH=false

COPY requirements.txt requirements-auth.txt ./
RUN if [ "$WITH_AUTH" = "true" ]; then \
        apt-get update && apt-get install -y --no-install-recommends git \
        && rm -rf /var/lib/apt/lists/* \
        && pip install --no-cache-dir -r requirements-auth.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

COPY app ./app
COPY wsgi.py ./

# uid fixe : c'est lui qui doit pouvoir lire la clé SSH montée dans le conteneur (voir README)
RUN useradd --system --uid 10001 --no-create-home appuser \
    && mkdir -p /data && chown appuser /data
USER appuser

# Données persistantes (minijeu actif) : volume Docker monté sur /data
ENV PORT=5000 \
    DATA_DIR=/data
EXPOSE ${PORT}

# 1 worker + des threads : les switchs de minijeu sont longs (streaming, jusqu'à plusieurs minutes)
# et le verrou « un switch à la fois » est en mémoire. Timeout élevé pour la même raison.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers ${GUNICORN_WORKERS:-1} --worker-class gthread --threads ${GUNICORN_THREADS:-8} --timeout ${GUNICORN_TIMEOUT:-300} --access-logfile - wsgi:app"]
