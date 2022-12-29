# https://docs.gunicorn.org/en/stable/settings.html#workers

workers = 7
threads = 10

capture_output = True
accesslog = "/app/log/gunicorn.access.log"
errorlog = "/app/log/gunicorn.error.log"
