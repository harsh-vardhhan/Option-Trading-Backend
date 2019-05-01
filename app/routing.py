from django.urls import path
from app.consumers import stock_consumer

websocket_urlpatterns = [
    path(r'^ws/$', stock_consumer)
]