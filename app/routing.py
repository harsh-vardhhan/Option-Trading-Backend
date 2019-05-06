
from django.urls import path
from app import consumers

websocket_urlpatterns = [
       path('ws/<id>/', consumers.stock_consumer)
]

# ws://localhost:8000/ws/123/
