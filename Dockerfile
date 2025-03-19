FROM python:3.12.8-slim-bullseye

ENV LC_ALL="fr_FR.utf8" \
    LC_CTYPE="fr_FR.utf8" \
    LANG="fr_FR.utf8" \
    LANGUAGE="fr_FR.UTF-8"

RUN apt-get update -y &&  \
    apt-get install -y cron curl gcc gettext krb5-user libkrb5-dev locales nginx procps sudo xxd && \
    rm -rf /var/lib/apt/lists/* && \
    localedef -i fr_FR -f UTF-8 fr_FR.UTF-8

ARG USER_UID=1000
ARG GROUP_UID=1050
ARG USERNAME=cohort360-backend
ARG GROUPNAME=$USERNAME
ARG HOMEDIR=/home/$USERNAME

WORKDIR $HOMEDIR/app

COPY . .
COPY .conf/nginx.conf /etc/nginx/

RUN groupadd --gid "$GROUP_UID" "$GROUPNAME" && \
    useradd --uid "$USER_UID" --gid "$GROUP_UID" --system --shell /bin/bash "$USERNAME" && \
    chown -R "$USERNAME":"$GROUPNAME" "$HOMEDIR" && \
    chmod +x docker-entrypoint.sh && \
    echo "$USERNAME ALL=(ALL) NOPASSWD: /usr/sbin/service, /usr/bin/crontab" >> /etc/sudoers.d/custom_sudo && \
    chmod 440 /etc/sudoers.d/custom_sudo

USER $USER_UID

ENV VIRTUAL_ENV=$HOMEDIR/app/.venv
ENV PATH="$HOMEDIR/app:$VIRTUAL_ENV/bin:$HOMEDIR/.local/bin:$PATH" \
    DEBIAN_FRONTEND=noninteractive

RUN pip install --no-cache-dir uv && \
    uv sync --frozen

ENTRYPOINT ["docker-entrypoint.sh"]