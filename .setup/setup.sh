#!/usr/bin/env bash
set -e

sudo apt update && sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y && sudo apt update

echo "Installing prerequisites..."
sudo apt install -y python3.12 python3.12-dev postgresql postgresql-contrib libkrb5-dev gcc
echo "Installed: Python $(python3.12 --version), PostgreSQL $(psql --version), Kerberos"

pip install uv
cd ..
uv venv -p python3.12
uv sync
source .venv/bin/activate
echo "Successfully initialized a virtual env and installed requirements"

COHORT_DB=$(sed -n 's/^DB_NAME=//p' admin_cohort/.env)
COHORT_USER=$(sed -n 's/^DB_USER=//p' admin_cohort/.env)
COHORT_USER_PASSWORD=$(sed -n 's/^DB_PASSWORD=//p' admin_cohort/.env)

echo "Creating database '$COHORT_DB' and a user '$COHORT_USER' with password '$COHORT_USER_PASSWORD'"

sudo -u postgres psql <<EOF
CREATE USER $COHORT_USER PASSWORD '$COHORT_USER_PASSWORD';
CREATE DATABASE $COHORT_DB OWNER $COHORT_USER;
GRANT ALL PRIVILEGES ON DATABASE $COHORT_DB TO $COHORT_USER;
ALTER USER $COHORT_USER CREATEDB;
EOF

echo "Database and user created. Running migrations..."

python manage.py migrate --database="default"

echo "Initializing a super user with all privileges"
python manage.py load_initial_data --perimeters-conf .setup/perimeters.example.csv

python manage.py runserver localhost:8000 &
echo "Dev server running on localhost:8000"
