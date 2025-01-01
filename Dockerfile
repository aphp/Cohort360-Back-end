FROM python:3.12.8-slim-bullseye

RUN apt-get update -y &&  \
    apt-get install -y cron curl gcc gettext krb5-user libkrb5-dev locales locales-all nginx procps sudo xxd && \
    rm -rf /var/lib/apt/lists/*

ARG USER_UID=1000
ARG GROUP_UID=1050
ARG USERNAME=cohort360-backend
ARG GROUPNAME=$USERNAME
ARG HOMEDIR=/home/$USERNAME

WORKDIR $HOMEDIR/app

COPY . .
COPY .conf/nginx.conf /etc/nginx/

ENV VIRTUAL_ENV=$HOMEDIR/app/.venv \
    PATH="$HOMEDIR/app:$PATH" \
    DEBIAN_FRONTEND=noninteractive \
    LC_ALL="fr_FR.utf8" \
    LC_CTYPE="fr_FR.utf8"

RUN pip install --no-cache-dir uv && \
    uv sync --frozen && \
    dpkg-reconfigure locales && \
    echo "$USERNAME ALL=(ALL) NOPASSWD: /bin/sed, /usr/sbin/service" >> /etc/sudoers.d/custom_sudo && \
    chmod 440 /etc/sudoers.d/custom_sudo && \
    groupadd --gid "$GROUP_UID" "$GROUPNAME" && \
    useradd --uid "$USER_UID" --gid "$GROUP_UID" --system --shell /bin/bash "$USERNAME" && \
    chown -R "$USERNAME":"$GROUPNAME" "$HOMEDIR" && \
    chmod +x docker-entrypoint.sh

USER $USER_UID

ENTRYPOINT ["docker-entrypoint.sh"]