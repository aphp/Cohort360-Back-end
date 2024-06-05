#!/usr/bin/env bash
set -e

sudo apt update && sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y && sudo apt update

# Python
echo "Installing prerequisites..."
sudo apt install -y python3.11 python3.11-dev postgresql postgresql-contrib libkrb5-dev gcc
echo "Installed: Python $(python3.11 --version), PostgreSQL $(psql --version), Kerberos"

pip install uv
uv venv -p python3.11 ../venv
source ../venv/bin/activate
uv pip install -r ../requirements.txt
echo "Successfully installed requirements"

COHORT_USER="cohort_dev"
COHORT_USER_PASSWORD="cohort_dev_pwd"
COHORT_DB="cohort_db"

sudo -u postgres psql <<EOF
CREATE USER $COHORT_USER PASSWORD '$COHORT_USER_PASSWORD';
CREATE DATABASE $COHORT_DB OWNER $COHORT_USER;
GRANT ALL PRIVILEGES ON DATABASE $COHORT_DB TO $COHORT_USER;
ALTER USER $COHORT_USER CREATEDB;
EOF

echo "Database and user created. Running migrations..."

source ../venv/bin/activate
python ../manage.py migrate --database="default"

echo "Initializing a user with administration privileges"
python ../manage.py load_initial_data --perimeters-conf perimeters.example.csv

echo "Running server..."
python ../manage.py runserver localhost:8000 &