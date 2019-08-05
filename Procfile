release: python manage.py migrate
worker: python worker.py
blackscholes: python blackscholes.py
newrelic-admin run-program gunicorn upstox_server.wsgi --log-file -