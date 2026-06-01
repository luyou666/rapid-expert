FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python scripts/harness_diag.py health >/dev/null || exit 1

CMD ["python", "scripts/harness_server.py", "--host", "0.0.0.0", "--port", "8765"]
