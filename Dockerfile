# syntax=docker/dockerfile:1
# 多架构镜像（linux/amd64, linux/arm64）：CI 同时构建，ARM64 为主要目标。
# 构建：docker buildx build --platform linux/arm64 -t mi-fitness-mcp-cn .
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # 数据、配置、日志统一落到 /data，便于挂载持久卷
    XDG_DATA_HOME=/data/share \
    XDG_CONFIG_HOME=/data/config \
    XDG_STATE_HOME=/data/state \
    # 容器内无 Secret Service，使用 keyrings.alt 文件后端（明文，仅存在于挂载卷内）
    PYTHON_KEYRING_BACKEND=keyrings.alt.file.PlaintextKeyring

WORKDIR /app

# 只复制构建所需文件，先装依赖再拷入口脚本，最大化层缓存
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install ".[all]" keyrings.alt

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown -R app:app /data

COPY docker/entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh

USER app
VOLUME ["/data"]
EXPOSE 8321 8322
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
# all = 同一容器内启动 FastAPI (8321) + Flask 仪表盘 (8322)
CMD ["all"]
