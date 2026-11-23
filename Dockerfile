FROM python:3.14.4-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt requirements_minimal.txt ./
COPY requirements/ ./requirements/
RUN python -m pip install -r requirements.txt \
    && useradd --create-home --uid 10001 edunaij
COPY --chown=edunaij:edunaij . .
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R edunaij:edunaij /app/staticfiles /app/media
USER edunaij
EXPOSE 8000
CMD ["bash", "scripts/railway-start.sh"]
