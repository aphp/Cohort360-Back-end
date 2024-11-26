#!/usr/bin/env bash

# Initialize option variables
WITH_CELERY_BEAT=""
WITH_KERBEROS=false
WITH_INIT=false
WITH_LOGGING=false
WITHOUT_APP_SERVER=false
WITH_DB_MIGRATION=false

# Parse options using getopts
while getopts "bkilnd" opt; do
    case $opt in
        b)
            WITH_CELERY_BEAT="-B"
            ;;
        k)
            WITH_KERBEROS=true
            ;;
        i)
            WITH_INIT=true
            ;;
        l)
            WITH_LOGGING=true
            ;;
        n)
            WITHOUT_APP_SERVER=true
            ;;
        d)
            WITH_DB_MIGRATION=true
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            usage
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            usage
            ;;
    esac
done

# Shift off the options and optional --.
shift "$((OPTIND-1))"

set -e

mkdir -p /app/log

sed -i s/{{BACK_HOST}}/"$BACK_HOST"/g /etc/nginx/nginx.conf;

service nginx restart

source $VIRTUAL_ENV/bin/activate

if [ "$WITH_DB_MIGRATION" = true ]; then
  python manage.py migrate --database="default"
  python manage.py collectstatic --noinput
fi

if [ "$WITH_INIT" = true ]; then
  set +e
  python manage.py load_initial_data --perimeters-conf /perimeters.csv
  set -e
fi

if [ "$WITH_KERBEROS" = true ]; then
  kinit $KERBEROS_USER -k -t akouachi.keytab || echo "kinit failed, continue app launching"
  # Cron kerberos token refresh
  crontab -l | { cat; echo "0 0 * * */1 /usr/bin/kinit akouachi@EDS.APHP.FR -k -t /app/akouachi.keytab"; } | crontab -
  cron
fi

if [ "$WITH_LOGGING" = true ]; then
  python setup_logging.py &
fi

if [ "$WITHOUT_APP_SERVER" = false ]; then
  celery -A admin_cohort worker $WITH_CELERY_BEAT --loglevel=INFO --logfile=/app/log/celery.log &
  sleep 5

  # For websockets
  daphne -p 8005 admin_cohort.asgi:application &

  gunicorn admin_cohort.wsgi --config .conf/gunicorn.conf.py

  tail -f /app/log/django.error.log
fi

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
