
from django.urls import path
from app import consumers

websocket_urlpatterns = [
       path('ws/<str:room_uuid>/', consumers.stock_consumer)
]