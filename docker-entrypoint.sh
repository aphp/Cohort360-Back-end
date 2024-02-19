#!/usr/bin/env bash
set -e

mkdir -p /app/log

sed -i s/{{BACK_HOST}}/"$BACK_HOST"/g /etc/nginx/nginx.conf;

service nginx restart

python manage.py migrate --database="default"
python manage.py collectstatic --noinput

# init kerberos
kinit $KERBEROS_USER -k -t akouachi.keytab
# Cron kerberos token refresh
crontab -l | { cat; echo "0 0 * * */1 /usr/bin/kinit akouachi@EDS.APHP.FR -k -t /app/akouachi.keytab"; } | crontab -
cron

# See https://docs.celeryq.dev/en/stable/reference/cli.html#celery-worker for configuration
celery -A admin_cohort worker -B --loglevel=INFO --logfile=/app/log/celery.log &
sleep 10

python setup_logging.py &
gunicorn admin_cohort.wsgi --config .conf/gunicorn.conf.py

# For websockets
daphne -p 8005 admin_cohort.asgi:application

tail -f /app/log/django.error.log

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
