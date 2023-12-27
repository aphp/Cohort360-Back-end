FROM harbor.eds.aphp.fr/cohort360/python:3.11.4-alpine AS builder
WORKDIR /tempapp
COPY . .
RUN apk add --no-cache krb5-dev build-base
RUN pip install --no-cache-dir -r /tempapp/requirements.txt


# use nginx alpine to match sys of builder image ? to avoid compatibility issues
FROM harbor.eds.aphp.fr/cohort360/nginx:1.21 AS final
WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive
# check maybe some of the packages is already present in nginx image
RUN apt-get update -y && apt-get install -y curl gettext locales locales-all xxd krb5-user nano cron
ENV LC_ALL="fr_FR.utf8"
ENV LC_CTYPE="fr_FR.utf8"
RUN dpkg-reconfigure locales

COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/sbin /usr/sbin
COPY --from=builder /usr/bin /usr/bin
RUN echo "-------- Contents of the /usr/sbin directory:" && ls -l /usr/sbin
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /tempapp /app
COPY .conf/nginx.conf /etc/nginx/
COPY docker-entrypoint.sh /app/

RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]