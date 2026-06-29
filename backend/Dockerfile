# ============================================================
# Backend — Python 3.12.13-alpine
# ============================================================
FROM python:3.12.13-alpine AS builder

WORKDIR /build

RUN apk add --no-cache \
    build-base \
    postgresql-dev \
    musl-dev \
    linux-headers \
    gcc \
    && rm -rf /var/cache/apk/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ---------- runtime ----------
FROM python:3.12.13-alpine

WORKDIR /app

# 仅安装运行时 libpq（psycopg2-binary 需要）
RUN apk add --no-cache \
    postgresql-libs \
    && rm -rf /var/cache/apk/*

# 从 builder 阶段复制已安装的 Python 包
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# 默认启动 uvicorn（也可通过 docker-compose command 覆盖启动 celery worker）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
