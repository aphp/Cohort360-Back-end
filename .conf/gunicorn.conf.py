# workers = multiprocessing.cpu_count() * 2 + 1
# max_requests = 10
threads = 10
# bind = "127.0.0.1:8000"

# Whether to send Django output to the error log
capture_output = True

accesslog = "/app/log/gunicorn.access.log"
errorlog = "/app/log/gunicorn.log"
