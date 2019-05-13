web: gunicorn upstox_server.wsgi --log-file -

release: python manage.py migrate
web: run-program waitress-serve --port=$PORT settings.wsgi:application
