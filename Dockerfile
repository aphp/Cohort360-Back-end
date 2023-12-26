FROM python:3.11.4-alpine as base
# Install needed dependencies]
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && apt-get install -y nginx curl gettext locales locales-all xxd krb5-user nano cron

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

FROM python:3.11.4-alpine
RUN apt-get update -y && apt-get install -y nginx cron
COPY --from=base /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=base /usr/bin/ /usr/bin/
#COPY --from=base /usr/sbin/ /usr/sbin/
COPY --from=base /usr/local/bin/ /usr/local/bin/

ENV LC_ALL="fr_FR.utf8"
ENV LC_CTYPE="fr_FR.utf8"
RUN dpkg-reconfigure locales

WORKDIR /app
COPY ./ ./

# Configure the nginx inside the docker image
COPY .conf/nginx.conf /etc/nginx/

# Entrypoint script is used to replace environment variables
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]