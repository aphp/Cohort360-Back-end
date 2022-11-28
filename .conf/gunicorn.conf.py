# bind = "127.0.0.1:8000"
# workers = multiprocessing.cpu_count() * 2 + 1
threads = 10

# Whether to send Django output to the error log
capture_output = True

# Access log - records incoming HTTP requests
accesslog = "app/log/gunicorn.access.log"

# Error log - records Gunicorn server goings-on
errorlog = "app/log/gunicorn.error.log"

# How verbose the Gunicorn error logs should be
loglevel = "info"