# 本地构建用 grok-register-base:latest
# CI 环境用 ghcr base 镜像（通过 --build-arg BASE_IMAGE=... 覆盖）
ARG BASE_IMAGE=ghcr.io/996code/grok-register-base:latest
FROM ${BASE_IMAGE}

WORKDIR /app

# 先复制 entrypoint（避免被 COPY . /app 覆盖）
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 安装 Python 依赖
COPY requirements.txt /app/requirements.txt
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . /app

# 创建运行时目录
RUN mkdir -p /app/output /app/screenshots /app/cpa_auths

ENV GROK_DOCKER=1
ENV GROK_AUTO_START=1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["cli"]
