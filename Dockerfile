FROM harbor.eds.aphp.fr/cohort360/python:3.11.4-slim-buster
WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && apt-get install -y net-tools procps nginx curl gettext locales locales-all xxd gcc libkrb5-dev krb5-user nano cron && rm \
    -rf /var/lib/apt/lists/*
ENV LC_ALL="fr_FR.utf8"
ENV LC_CTYPE="fr_FR.utf8"
RUN dpkg-reconfigure locales

COPY . .
RUN pip install --upgrade pip && pip install uv
RUN uv venv && uv pip install --no-cache -r requirements.txt

COPY .conf/nginx.conf /etc/nginx/
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]