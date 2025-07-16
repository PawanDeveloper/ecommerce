"""
WebSocket consumers for real-time order status updates.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Order

User = get_user_model()


class OrderStatusConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time order status updates.
    """
    
    async def connect(self):
        """Accept WebSocket connection if user is authenticated and owns the order."""
        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.group_name = f'order_{self.order_id}'
        
        # Check authentication and order ownership
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
            
        # Check if user owns the order
        order_exists = await self.check_order_ownership(user, self.order_id)
        if not order_exists:
            await self.close()
            return
        
        # Join order-specific group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current order status
        await self.send_order_status()

    async def disconnect(self, close_code):
        """Leave the order group."""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket data."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'get_status':
                await self.send_order_status()
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))

    async def order_status_update(self, event):
        """Send order status update to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'order_status_update',
            'order_id': event['order_id'],
            'status': event['status'],
            'message': event.get('message', ''),
            'timestamp': event.get('timestamp'),
        }))

    async def order_event(self, event):
        """Send order event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'order_event',
            'order_id': event['order_id'],
            'event_type': event['event_type'],
            'message': event['message'],
            'timestamp': event.get('timestamp'),
        }))

    @database_sync_to_async
    def check_order_ownership(self, user, order_id):
        """Check if the user owns the order."""
        try:
            Order.objects.get(id=order_id, user=user)
            return True
        except Order.DoesNotExist:
            return False

    @database_sync_to_async
    def get_order_status(self):
        """Get current order status."""
        try:
            order = Order.objects.get(id=self.order_id)
            return {
                'order_id': str(order.id),
                'order_number': order.order_number,
                'status': order.status,
                'payment_status': order.payment_status,
                'created_at': order.created_at.isoformat(),
                'updated_at': order.updated_at.isoformat(),
            }
        except Order.DoesNotExist:
            return None

    async def send_order_status(self):
        """Send current order status."""
        order_data = await self.get_order_status()
        if order_data:
            await self.send(text_data=json.dumps({
                'type': 'order_status',
                **order_data
            }))


class UserOrdersConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user's all orders updates.
    """
    
    async def connect(self):
        """Accept WebSocket connection if user is authenticated."""
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
            
        self.user_id = user.id
        self.group_name = f'user_orders_{self.user_id}'
        
        # Join user-specific group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        """Leave the user orders group."""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket data."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'get_orders':
                await self.send_user_orders()
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))

    async def new_order(self, event):
        """Send new order notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'order_id': event['order_id'],
            'order_number': event['order_number'],
            'total_amount': str(event['total_amount']),
            'timestamp': event.get('timestamp'),
        }))

    async def order_update(self, event):
        """Send order update notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'order_id': event['order_id'],
            'status': event['status'],
            'message': event.get('message', ''),
            'timestamp': event.get('timestamp'),
        }))

    @database_sync_to_async
    def get_user_orders(self):
        """Get user's recent orders."""
        try:
            user = User.objects.get(id=self.user_id)
            orders = user.orders.all()[:10]  # Get last 10 orders
            return [
                {
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'status': order.status,
                    'payment_status': order.payment_status,
                    'total_amount': str(order.total_amount),
                    'created_at': order.created_at.isoformat(),
                }
                for order in orders
            ]
        except User.DoesNotExist:
            return []

    async def send_user_orders(self):
        """Send user's orders list."""
        orders_data = await self.get_user_orders()
        await self.send(text_data=json.dumps({
            'type': 'user_orders',
            'orders': orders_data
        })) 