"""
WSGI config for upstox_server project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""

import os
import newrelic.agent

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "upstox_server.settings")

from django.core.wsgi import get_wsgi_application


application = get_wsgi_application()


newrelic.agent.initialize(os.path.join(os.path.dirname(__file__), "newrelic.ini"))
application = newrelic.agent.WSGIApplicationWrapper(application)
