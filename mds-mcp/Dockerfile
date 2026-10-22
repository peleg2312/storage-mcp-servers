FROM ghcr.io/astral-sh/uv:python3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8000 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY main.py entry.py mds_extra.py mcp_auth.py ./

RUN chgrp -R 0 /app && chmod -R g=u /app
USER 1001
EXPOSE 8000
CMD ["python", "entry.py"]
