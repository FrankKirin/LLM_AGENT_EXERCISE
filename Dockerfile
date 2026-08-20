
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /build

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIROMENT=/build/.venv

# 拷贝依赖描述文件
COPY pyproject.toml uv.lock ./

# 安装生产依赖
# --frozen: 严格使用lock文件，不重新解析
# --no-install-project: 只安装依赖，不装当前项目
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.11-slim AS runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    APP_HOME=/app

WORKDIR ${APP_HOME}}

COPY --from=builder /build/.venv ${APP_HOME}/.venv

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/list/*

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

COPY --chown=appuser:appuser . .

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查：每30s查一次，超时3s，3次失败标记为不健康
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]