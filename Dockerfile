FROM python:3.11.4-slim-buster AS builder
WORKDIR /app

ENV VIRTUAL_ENV=/app/venv
RUN apt-get update -y && apt-get install -y gcc libkrb5-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install uv && uv venv $VIRTUAL_ENV && uv pip install --no-cache -r requirements.txt

FROM python:3.11.4-slim-buster AS final
WORKDIR /app

ENV VIRTUAL_ENV=/app/venv \
    PATH="$VIRTUAL_ENV/bin:$PATH" \
    DEBIAN_FRONTEND=noninteractive \
    LC_ALL="fr_FR.utf8" \
    LC_CTYPE="fr_FR.utf8"

RUN apt-get update -y \
    && apt-get install -y cron curl gettext krb5-user locales locales-all nano nginx procps xxd \
    && rm -rf /var/lib/apt/lists/*
RUN dpkg-reconfigure locales

COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
COPY . .
COPY .conf/nginx.conf /etc/nginx/
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]