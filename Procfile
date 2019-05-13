release: python manage.py migrate
web: gunicorn upstox_server.wsgi --log-file -

web: daphne upstox_server.asgi:channel_layer --port $PORT --bind 0.0.0.0 -v2
chatworker: python manage.py runworker --settings=upstox_server.settings -v2
