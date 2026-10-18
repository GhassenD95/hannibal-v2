FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Repo-root package layout: modules resolve legal-packs/ and
# tests/evaluation/fixtures.json relative to the repository root.
COPY apps/__init__.py ./apps/__init__.py
COPY apps/api ./apps/api
COPY legal-packs ./legal-packs
COPY tests/evaluation/fixtures.json ./tests/evaluation/fixtures.json
COPY scripts ./scripts

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
