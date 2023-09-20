# build stage
FROM harbor.eds.aphp.fr/cohort360/python:3.11.4-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# final stage
FROM harbor.eds.aphp.fr/cohort360/python:3.11.4-slim

WORKDIR /app

COPY --from=builder /app/wheels /wheels
COPY ./ ./
COPY .conf/nginx.conf /etc/nginx/

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL="fr_FR.utf8"
ENV LC_CTYPE="fr_FR.utf8"

RUN apt-get update -y && apt-get install -y nginx curl gettext locales locales-all xxd krb5-user nano cron
RUN dpkg-reconfigure locales

RUN pip install --no-cache /wheels/*

RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
