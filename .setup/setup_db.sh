#!/usr/bin/env bash
set -e

PG_PORT=5432

COHORT_USER="cohort_dev"
COHORT_USER_PASSWORD="cohort_user_pwd"
COHORT_DB="cohort_db"

sudo -u postgres psql <<EOF
CREATE USER $COHORT_USER PASSWORD $COHORT_USER_PASSWORD;
CREATE DATABASE $COHORT_DB OWNER $COHORT_USER;
GRANT ALL PRIVILEGES ON DATABASE $COHORT_DB TO $COHORT_USER;
ALTER USER $COHORT_USER CREATEDB;
EOF

echo "Database and user setup completed."
echo "Running Django migrations..."

source ../venv/bin/activate
python manage.py migrate

echo "Done! Successfully added tables into database."
echo "Inserting initial data..."
PGPASSWORD=$COHORT_USER_PASSWORD psql -h localhost -p $PG_PORT -d $COHORT_DB -U $COHORT_USER -f init_data.sql