#!/usr/bin/env bash
set -e

mkdir -p /app/log

sed -i s/{{BACK_HOST}}/"$BACK_HOST"/g /etc/nginx/nginx.conf;

service nginx restart

source $VIRTUAL_ENV/bin/activate
python manage.py migrate --database="default"
python manage.py collectstatic --noinput

kinit $KERBEROS_USER -k -t akouachi.keytab || echo "kinit failed, continue app launching"
# Cron kerberos token refresh
crontab -l | { cat; echo "0 0 * * */1 /usr/bin/kinit akouachi@EDS.APHP.FR -k -t /app/akouachi.keytab"; } | crontab -
cron

celery -A admin_cohort worker --loglevel=INFO --logfile=/app/log/celery.log &
sleep 5

python setup_logging.py &
# For websockets
daphne -p 8005 admin_cohort.asgi:application &

gunicorn admin_cohort.wsgi --config .conf/gunicorn.conf.py

tail -f /app/log/django.error.log

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
