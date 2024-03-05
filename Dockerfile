FROM harbor.eds.aphp.fr/cohort360/python:3.11.4-slim-buster AS builder
WORKDIR /tempapp
COPY requirements.txt .
RUN apt-get update -y && apt-get install -y gcc libkrb5-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip && pip install uv
RUN uv venv && uv pip install --no-cache -r requirements.txt

FROM harbor.eds.aphp.fr/cohort360/python:3.11.4-slim-buster AS final
WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && apt-get install -y net-tools procps vim nginx curl gettext locales locales-all xxd krb5-user nano cron && rm -rf /var/lib/apt/lists/*
ENV LC_ALL="fr_FR.utf8"
ENV LC_CTYPE="fr_FR.utf8"
RUN dpkg-reconfigure locales

COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY . .
COPY .conf/nginx.conf /etc/nginx/
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]