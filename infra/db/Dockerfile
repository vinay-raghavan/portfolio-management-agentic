FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /workspace

COPY ./pyproject.toml ./uv.lock ./
COPY ./infra/db ./infra/db

RUN uv sync --frozen --group dev

CMD ["uv", "run", "alembic", "-c", "infra/db/alembic.ini", "upgrade", "head"]
