#!/usr/bin/env bash
set -e

apps=(accesses admin_cohort cohort exports workspaces)

for app in "${apps[@]}"
do
  echo "cleaning migrations history for app: $app"
  python manage.py migrate --fake $app zero
done

for app in "${apps[@]}"
do
  echo "deleting migration for app: $app"
  find $app -path "*/migrations/*" -not -name "__init__.py" -delete
done

echo "make migrations"
python manage.py makemigrations

echo "migrate with fake-initial"
python manage.py migrate --fake-initial

echo "migrations squashed successfully!"