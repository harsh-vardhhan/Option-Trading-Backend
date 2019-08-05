release: python manage.py migrate
web: gunicorn upstox_server.wsgi --log-file -
worker: python worker.py
blackscholes: python blackscholes.py