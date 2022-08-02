#!/usr/bin/env bash
set -e


mkdir -p static/ /app/log

# update variables in nginx
declare -a UrlArray=("BACK_URL_LOCAL")
for NAME in ${UrlArray[@]}; do
  ENV_VAR="${!NAME}"
  ENV_VAR=$(echo $ENV_VAR | sed "s/[^a-zA-Z0-9]/\\\\&/g");
  sed -i s/"{{"$NAME"}}"/$ENV_VAR/g /etc/nginx/sites-enabled/nginx.conf;
done

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

python manage.py runserver 49040 >> /app/log/django.log 2>&1 &

tail -f /app/log/django.log
