#!/usr/bin/env bash
set -e

apps=(admin_cohort accesses cohort exports workspaces)

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

mv cohort/extra_migrations/* cohort/migrations
mv exports/extra_migrations/* exports/migrations

rm -rf cohort/extra_migrations
rm -rf exports/extra_migrations

echo "migrate with fake initial"
python manage.py migrate --fake-initial

echo "migrations squashed successfully!"