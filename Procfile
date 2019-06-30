release: python manage.py migrate
web: gunicorn upstox_server.wsgi.py --log-file -
worker: python worker.py
blackscholes: python blackscholes.py
web: upstox_server.wsgi:application --port $PORT --bind 0.0.0.0 -v2

