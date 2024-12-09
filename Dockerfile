ARG IMAGE_FROM="python:3.11.4-slim-buster"

FROM ${IMAGE_FROM} AS builder
WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
RUN apt-get update -y && apt-get install -y gcc libkrb5-dev && rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml .
RUN pip install uv && uv sync

FROM ${IMAGE_FROM} AS final
WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH" \
    DEBIAN_FRONTEND=noninteractive \
    LC_ALL="fr_FR.utf8" \
    LC_CTYPE="fr_FR.utf8"

RUN apt-get update -y \
    && apt-get install -y cron curl gettext krb5-user locales locales-all nginx procps xxd \
    && rm -rf /var/lib/apt/lists/* \
    && dpkg-reconfigure locales

COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
COPY . .
COPY .conf/nginx.conf /etc/nginx/
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]