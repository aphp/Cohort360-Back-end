ARG IMAGE_FROM="python:3.11.4-slim-buster"

FROM ${IMAGE_FROM} AS builder
WORKDIR /temp

RUN apt-get update -y &&  \
    apt-get install -y gcc libkrb5-dev && \
    rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml .
RUN pip install uv && \
    uv sync

FROM ${IMAGE_FROM} AS final

ARG USER_UID=1000
ARG GROUP_UID=1050
ARG USERNAME=cohort360-backend
ARG GROUPNAME=$USERNAME
ARG HOMEDIR=/home/$USERNAME
ARG WORKDIR=$HOMEDIR/app

WORKDIR $WORKDIR

ENV VIRTUAL_ENV=$WORKDIR/.venv \
    PATH="$WORKDIR:$PATH" \
    DEBIAN_FRONTEND=noninteractive \
    LC_ALL="fr_FR.utf8" \
    LC_CTYPE="fr_FR.utf8"

RUN apt-get update -y && \
    apt-get install -y cron curl gettext krb5-user locales locales-all nginx procps sudo xxd && \
    rm -rf /var/lib/apt/lists/* && \
    dpkg-reconfigure locales && \
    echo "$USERNAME ALL=(ALL) NOPASSWD: /usr/sbin/nginx, /bin/sed" >> /etc/sudoers.d/sudo_nginx && \
    echo "Defaults:$USERNAME !requiretty" >> /etc/sudoers.d/no_tty

COPY --from=builder /temp/.venv $VIRTUAL_ENV
COPY . .
COPY .conf/nginx.conf /etc/nginx/

RUN groupadd --gid $GROUP_UID $GROUPNAME && \
    useradd --uid $USER_UID --gid $GROUP_UID --create-home --system --shell /bin/bash $USERNAME && \
    chown -R $USERNAME:$GROUPNAME $HOMEDIR && \
    chmod +x docker-entrypoint.sh

USER $USER_UID

ENTRYPOINT ["docker-entrypoint.sh"]