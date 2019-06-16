release: python manage.py migrate app
web: gunicorn upstox_server.wsgi --log-file -
worker: python worker.py
web: daphne upstox_server.asgi:application --port $PORT --bind 0.0.0.0 -v2
chatworker: python manage.py clear_cache runworker --settings=upstox_server.settings -v2
