#!/usr/bin/env bash
set -e

bash prerequisites.sh
bash virtual_env.sh

mkdir log

sed -i s/{{BACK_HOST}}/"$BACK_HOST"/g /etc/nginx/nginx.conf;

service nginx restart

python manage.py migrate --database="default"
python manage.py collectstatic --noinput

celery -A admin_cohort worker -B --loglevel=INFO --logfile=/app/log/celery.log &
sleep 5

# For websockets
daphne -p 8005 admin_cohort.asgi:application &

python setup_logging.py &
gunicorn admin_cohort.wsgi --config .conf/gunicorn.conf.py

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
