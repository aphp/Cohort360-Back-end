FROM harbor.eds.aphp.fr/cohort360/python:3.7.10

WORKDIR /app
COPY ./ ./

# Install needed dependencies]
RUN echo "proxies:"
RUN echo "$http_proxy"
RUN echo "$https_proxy"
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && apt-get install -y nginx curl gettext locales locales-all xxd krb5-user nano cron

# Configure the nginx inside the docker image
COPY docker/nginx.conf /etc/nginx/sites-enabled/

# Install requirement for python
RUN pip install -r requirements.txt
ENV LC_ALL="fr_FR.utf8"
ENV LC_CTYPE="fr_FR.utf8"
RUN dpkg-reconfigure locales


# Entrypoint script is used to replace environment variables
RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]