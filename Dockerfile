FROM python:3.11.4-alpine as builder
WORKDIR /app
COPY requirements.txt .
RUN apk add --no-cache krb5-user build-base
RUN pip install --no-cache-dir -r /app/requirements.txt


FROM harbor.eds.aphp.fr/cohort360/nginx:1.21
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && apt-get install -y nginx curl gettext locales locales-all xxd krb5-user nano cron
ENV LC_ALL="fr_FR.utf8"
ENV LC_CTYPE="fr_FR.utf8"
RUN dpkg-reconfigure locales

WORKDIR /app
COPY . .
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY .conf/nginx.conf /etc/nginx/

RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]