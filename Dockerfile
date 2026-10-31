FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/srv/backend
COPY pyproject.toml alembic.ini ./
COPY backend ./backend
COPY infrastructure ./infrastructure
COPY scripts ./scripts
RUN pip install --no-cache-dir '.[test]' && useradd --uid 10001 --create-home lab
USER 10001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
