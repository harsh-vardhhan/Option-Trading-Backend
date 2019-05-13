release: python manage.py migrate
web: gunicorn upstox_server.wsgi --log-file -

web: daphne upstox_server.asgi:application --port $PORT --bind 0.0.0.0 -v2
chatworker: python manage.py clear_cache runworker --settings=upstox_server.settings -v2
