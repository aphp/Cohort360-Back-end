FROM harbor.eds.aphp.fr/cohort360/python:3.11.4-slim-buster AS builder
WORKDIR /tempapp
COPY requirements.txt .
RUN apt-get update -y && apt-get install -y gcc libkrb5-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

FROM harbor.eds.aphp.fr/cohort360/python:3.11.4-slim-buster AS final
RUN addgroup --system django && adduser --system --group django
ENV HOME=/app
WORKDIR $HOME

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && apt-get install -y nginx curl gettext locales locales-all xxd krb5-user nano cron && rm -rf /var/lib/apt/lists/*
ENV LC_ALL="fr_FR.utf8"
ENV LC_CTYPE="fr_FR.utf8"
RUN dpkg-reconfigure locales

COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY . $HOME
RUN chown -R django:django $HOME
COPY .conf/nginx.conf /etc/nginx/
RUN chmod +x docker-entrypoint.sh
USER django
ENTRYPOINT ["docker-entrypoint.sh"]