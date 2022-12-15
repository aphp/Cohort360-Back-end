#!/usr/bin/env bash
set -e

mkdir -p static/ /app/log

# update variables in nginx
sed -i s/{{BACK_URL_LOCAL}}/$BACK_URL_LOCAL/g /etc/nginx/nginx.conf;

# restart nginx
service nginx restart

python manage.py migrate --database="default"
python manage.py collectstatic --noinput

# init kerberos
kinit $KERBEROS_USER -k -t akouachi.keytab
# Cron kerberos token refresh
crontab -l | { cat; echo "0 0 * * */1 /usr/bin/kinit akouachi@EDS.APHP.FR -k -t /app/akouachi.keytab"; } | crontab -
cron

chmod 666 /app/log/celery.log

# See https://docs.celeryq.dev/en/stable/reference/cli.html#celery-worker for configuration
# and https://stackoverflow.com/a/59659476 for superuser privileges
celery worker -beat -A admin_cohort --concurrency=10 --loglevel INFO --logfile /app/log/celery.log --detach --uid=nobody --gid=nogroup

gunicorn admin_cohort.wsgi --config .conf/gunicorn.conf.py
