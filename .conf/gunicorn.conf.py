# https://docs.gunicorn.org/en/stable/settings.html#workers

workers = 7
threads = 10

capture_output = True   # Whether to send Django output to the error log
accesslog = "/app/log/gunicorn.access.log"
errorlog = "/app/log/gunicorn.log"
