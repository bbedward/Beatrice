FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY beatrice ./beatrice
COPY scripts ./scripts

FROM python:3.13-slim

RUN useradd --uid 1000 --create-home beatrice
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
USER beatrice

CMD ["python", "-m", "beatrice"]
