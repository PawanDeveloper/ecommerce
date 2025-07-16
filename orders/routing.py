"""
WebSocket routing for orders app.
"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/orders/<str:order_id>/', consumers.OrderStatusConsumer.as_asgi()),
    path('ws/orders/', consumers.UserOrdersConsumer.as_asgi()),
] 