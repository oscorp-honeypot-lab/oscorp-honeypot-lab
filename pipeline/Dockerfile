FROM python:3.12.4-slim-bookworm@sha256:a3e58f9399353be051735f09be0316bfdeab571a5c6a24fd78b92df85bcb2d85

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --gid 10001 oscorp \
    && useradd --uid 10001 --gid oscorp --create-home --shell /usr/sbin/nologin oscorp

WORKDIR /app

COPY pipeline/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY pipeline/alembic.ini /app/alembic.ini
COPY pipeline/migrations /app/migrations
COPY pipeline/contracts /app/contracts
COPY pipeline/alerts /app/alerts
COPY pipeline/geo /app/geo
COPY pipeline/risk /app/risk
COPY pipeline/tests /app/tests
COPY pipeline/pipeline_worker.py /app/pipeline_worker.py
COPY scripts/process_cowrie_ndjson.py /app/process_cowrie_ndjson.py
COPY scripts/recalculate_risk_scores.py /app/recalculate_risk_scores.py

USER oscorp

CMD ["python", "/app/process_cowrie_ndjson.py"]
