FROM grok-register-base:latest

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt || true

COPY . /app

RUN mkdir -p /app/output /app/screenshots /app/cpa_auths

ENV GROK_DOCKER=1
ENV GROK_AUTO_START=1

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["cli"]
