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

celery worker -B -A admin_cohort --loglevel=info >> /app/log/celery.log 2>&1 &

sleep 10

gunicorn admin_cohort.wsgi --config .conf/gunicorn.conf.py
