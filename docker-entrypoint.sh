#!/bin/bash

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

mkdir -p log

sudo sed -i s/{{BACKEND_HOST}}/"$BACKEND_HOST"/g /etc/nginx/nginx.conf;

sudo service nginx restart

source "$VIRTUAL_ENV"/bin/activate

if [ "$WITH_DB_MIGRATION" = true ]; then
  python manage.py migrate --database="default"
fi

if [ "$WITH_INIT" = true ]; then
  set +e
  python manage.py load_initial_data --perimeters-conf /perimeters.csv
  set -e
fi

if [ "$WITH_KERBEROS" = true ]; then
  kinit "$KERBEROS_USER" -kt akouachi.keytab || echo "kinit failed, continue app launching"
  # Cron kerberos ticket refresh
  echo "0 0 * * * su - $(whoami) -c 'kinit $KERBEROS_USER -kt $HOME/app/akouachi.keytab'" | sudo crontab -u root -
  sudo service cron start
fi

if [ "$WITH_LOGGING" = true ]; then
  python setup_logs_collector.py &
  if [ "$WITHOUT_APP_SERVER" = true ]; then
    wait -n
  fi
fi

if [ "$WITHOUT_APP_SERVER" = false ]; then
  python manage.py collectstatic --noinput

  celery -A admin_cohort worker $WITH_CELERY_BEAT --loglevel=INFO &
  sleep 5

  # For websockets
  daphne -v 0 -p 8005 admin_cohort.asgi:application &

  gunicorn admin_cohort.wsgi --config .conf/gunicorn.conf.py

  tail -f log/django.error.log &

  # Wait for any process to exit
  wait -n
fi

# Exit with status of process that exited first
exit $?
