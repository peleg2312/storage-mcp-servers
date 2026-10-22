FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8000 \
    DOCS_DIR=/data/docs INDEX_DB=/data/index/docs.db

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py docs_index.py mcp_auth.py ./
COPY sync/ ./sync/
COPY sources/ ./sources/

RUN chgrp -R 0 /app && chmod -R g=u /app
USER 1001
EXPOSE 8000
# default: the MCP server. The sync CronJob runs: python sync/sync_dell.py && python docs_index.py
CMD ["python3", "server.py"]
