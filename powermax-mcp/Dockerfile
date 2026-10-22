FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8000

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py mcp_auth.py ./

RUN chgrp -R 0 /app && chmod -R g=u /app
USER 1001
EXPOSE 8000
CMD ["python3", "server.py"]
