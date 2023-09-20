FROM python:3.11.4

WORKDIR /app
COPY ./ ./

# Install needed dependencies]
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && apt-get install -y nginx curl gettext locales locales-all xxd krb5-user nano cron

# Configure the nginx inside the docker image
COPY .conf/nginx.conf /etc/nginx/

# Install requirement for python
RUN pip install -r requirements.txt
ENV LC_ALL="fr_FR.utf8"
ENV LC_CTYPE="fr_FR.utf8"
RUN dpkg-reconfigure locales


# Entrypoint script is used to replace environment variables
RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]