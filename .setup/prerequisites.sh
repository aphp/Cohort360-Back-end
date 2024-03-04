#!/usr/bin/env bash
set -e

apt update && apt upgrade
apt install software-properties-common -y
add-apt-repository ppa:deadsnakes/ppa -y
apt update

# Python
echo "Installing Python..."
apt install python3.11 -y
apt install python3.11-dev
echo "Python installed: $(python3.11 --version)"

# PostgreSQL
echo "Installing PostgreSQL..."
apt install postgresql postgresql-contrib
echo "PostgreSQL installed: $(psql --version)"

# Kerberos for HDFS auth
echo "Installing Kerberos..."
apt install -y libkrb5-dev gcc
echo "Kerberos installed"