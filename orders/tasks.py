"""
Celery tasks for order processing.
"""
from celery import shared_task, chain
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
import logging

from .models import Order, OrderItem, OrderEvent
from cart.models import Cart
from core.models import AuditLog

User = get_user_model()
logger = logging.getLogger('ecommerce')


@shared_task(bind=True, max_retries=3)
def validate_inventory(self, user_id, cart_id, order_data):
    """
    Task 1: Validate inventory availability for all cart items.
    """
    try:
        logger.info(f"Starting inventory validation for cart {cart_id}")
        
        cart = Cart.objects.get(id=cart_id)
        validation_results = []
        
        for item in cart.items.all():
            # Check product availability
            if item.product.status != 'active':
                raise ValueError(f"Product {item.product.name} is no longer available")
            
            # Check stock for variants or products
            if item.variant:
                if not item.variant.is_in_stock:
                    raise ValueError(f"Product variant {item.variant.name} is out of stock")
                if item.quantity > item.variant.stock_quantity:
                    raise ValueError(
                        f"Only {item.variant.stock_quantity} items available for {item.variant.name}"
                    )
                validation_results.append({
                    'type': 'variant',
                    'id': item.variant.id,
                    'quantity': item.quantity,
                    'available': item.variant.stock_quantity
                })
            else:
                if not item.product.is_in_stock:
                    raise ValueError(f"Product {item.product.name} is out of stock")
                if item.product.track_inventory and item.quantity > item.product.stock_quantity:
                    raise ValueError(
                        f"Only {item.product.stock_quantity} items available for {item.product.name}"
                    )
                validation_results.append({
                    'type': 'product',
                    'id': item.product.id,
                    'quantity': item.quantity,
                    'available': item.product.stock_quantity if item.product.track_inventory else None
                })
        
        logger.info(f"Inventory validation successful for cart {cart_id}")
        return {
            'user_id': user_id,
            'cart_id': cart_id,
            'order_data': order_data,
            'validation_results': validation_results,
            'status': 'validated'
        }
        
    except Exception as exc:
        logger.error(f"Inventory validation failed for cart {cart_id}: {str(exc)}")
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        raise exc


@shared_task(bind=True, max_retries=3)
def create_order(self, validation_data):
    """
    Task 2: Create order from validated cart data.
    """
    cart_id = "unknown"
    try:
        # Handle old tasks that don't have user_id
        if 'user_id' not in validation_data:
            logger.error("Old task format detected - missing user_id, skipping")
            return {
                'error': 'Old task format, skipping',
                'status': 'skipped'
            }
            
        user_id = validation_data['user_id']
        cart_id = validation_data['cart_id']
        order_data = validation_data['order_data']
        
        logger.info(f"Creating order from cart {cart_id}")
        
        with transaction.atomic():
            cart = Cart.objects.select_for_update().get(id=cart_id)
            
            # Get user object and add to order data
            user = User.objects.get(id=user_id)
            order_data['user'] = user
            
            # Create order
            order = Order.objects.create(**order_data)
            
            # Create order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    variant=cart_item.variant,
                    product_name=cart_item.product.name,
                    variant_name=cart_item.variant.name if cart_item.variant else '',
                    product_sku=cart_item.variant.sku if cart_item.variant else cart_item.product.sku,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.unit_price,
                    total_price=cart_item.total_price
                )
            
            # Create order event
            OrderEvent.objects.create(
                order=order,
                event_type='created',
                message=f'Order {order.order_number} created successfully',
                metadata={'cart_id': str(cart_id)}
            )
            
            logger.info(f"Order {order.order_number} created successfully")
            
            return {
                'order_id': str(order.id),
                'order_number': order.order_number,
                'cart_id': cart_id,
                'validation_results': validation_data['validation_results'],
                'status': 'created'
            }
            
    except Exception as exc:
        logger.error(f"Order creation failed for cart {cart_id}: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        raise exc


@shared_task(bind=True, max_retries=3)
def deduct_stock(self, order_data):
    """
    Task 3: Deduct stock from products/variants.
    """
    try:
        order_id = order_data['order_id']
        validation_results = order_data['validation_results']
        
        logger.info(f"Deducting stock for order {order_id}")
        
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)
            
            # Deduct stock for each item
            for item_data in validation_results:
                if item_data['type'] == 'variant':
                    from products.models import ProductVariant
                    variant = ProductVariant.objects.select_for_update().get(id=item_data['id'])
                    variant.reduce_stock(item_data['quantity'])
                    
                    # Log stock change
                    AuditLog.objects.create(
                        model_name='ProductVariant',
                        object_id=str(variant.id),
                        action='stock_change',
                        field_name='stock_quantity',
                        old_value=str(variant.stock_quantity + item_data['quantity']),
                        new_value=str(variant.stock_quantity),
                        metadata={
                            'order_id': str(order.id),
                            'reason': 'order_created',
                            'quantity_deducted': item_data['quantity']
                        }
                    )
                    
                elif item_data['type'] == 'product':
                    from products.models import Product
                    product = Product.objects.select_for_update().get(id=item_data['id'])
                    if product.track_inventory:
                        product.reduce_stock(item_data['quantity'])
                        
                        # Log stock change
                        AuditLog.objects.create(
                            model_name='Product',
                            object_id=str(product.id),
                            action='stock_change',
                            field_name='stock_quantity',
                            old_value=str(product.stock_quantity + item_data['quantity']),
                            new_value=str(product.stock_quantity),
                            metadata={
                                'order_id': str(order.id),
                                'reason': 'order_created',
                                'quantity_deducted': item_data['quantity']
                            }
                        )
            
            # Update order status
            order.status = 'confirmed'
            order.save(update_fields=['status'])
            
            # Create order event
            OrderEvent.objects.create(
                order=order,
                event_type='confirmed',
                message=f'Order {order.order_number} confirmed and stock deducted',
                metadata={'stock_deductions': validation_results}
            )
            
            logger.info(f"Stock deducted successfully for order {order.order_number}")
            
            return {
                'order_id': order_id,
                'order_number': order.order_number,
                'cart_id': order_data['cart_id'],
                'status': 'stock_deducted'
            }
            
    except Exception as exc:
        logger.error(f"Stock deduction failed for order {order_id}: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        raise exc


@shared_task(bind=True, max_retries=3)
def send_confirmation(self, order_data):
    """
    Task 4: Send order confirmation email (simulated with logging).
    """
    try:
        order_id = order_data['order_id']
        order_number = order_data['order_number']
        cart_id = order_data['cart_id']
        
        logger.info(f"Sending confirmation for order {order_number}")
        
        # Get order for email data
        order = Order.objects.get(id=order_id)
        
        # Simulate sending email 
        logger.info(f"""
        ========== ORDER CONFIRMATION ==========
        Order Number: {order.order_number}
        Customer: {order.user.full_name} ({order.user.email})
        Total Items: {order.total_items}
        Total Amount: ${order.total_amount}
        
        Shipping Address:
        {order.shipping_address}
        
        Order Items:
        """)
        
        for item in order.items.all():
            logger.info(f"  - {item.product_name} x{item.quantity} = ${item.total_price}")
        
        logger.info("========== END CONFIRMATION ==========")
        
        # Clear cart after successful order
        try:
            cart = Cart.objects.get(id=cart_id)
            cart.clear()
            logger.info(f"Cart {cart_id} cleared after successful order")
        except Cart.DoesNotExist:
            logger.warning(f"Cart {cart_id} not found for clearing")
        
        # Create order event
        OrderEvent.objects.create(
            order=order,
            event_type='confirmation_sent',
            message=f'Confirmation email sent for order {order.order_number}',
            metadata={'email_sent': True}
        )
        
        logger.info(f"Order confirmation completed for order {order_number}")
        
        return {
            'order_id': order_id,
            'order_number': order_number,
            'status': 'completed'
        }
        
    except Exception as exc:
        logger.error(f"Confirmation sending failed for order {order_id}: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        raise exc


@shared_task
def process_checkout(user_id, cart_id, order_data):
    """
    Main task that chains the checkout process.
    """
    logger.info(f"Starting checkout process for user {user_id}, cart {cart_id}")
    
    # Create task chain
    checkout_chain = chain(
        validate_inventory.s(user_id, cart_id, order_data),
        create_order.s(),
        deduct_stock.s(),
        send_confirmation.s()
    )
    
    # Execute the chain
    result = checkout_chain.apply_async()
    
    logger.info(f"Checkout chain started with task ID: {result.id}")
    return result.id


@shared_task
def cleanup_abandoned_carts():
    """
    Periodic task to clean up abandoned carts.
    """
    from django.utils import timezone
    from datetime import timedelta
    
    # Delete carts older than 30 days with no user or older than 7 days for guest users
    cutoff_date_guest = timezone.now() - timedelta(days=7)
    cutoff_date_user = timezone.now() - timedelta(days=30)
    
    # Clean guest carts
    abandoned_guest_carts = Cart.objects.filter(
        user__isnull=True,
        updated_at__lt=cutoff_date_guest
    ).count()
    
    Cart.objects.filter(
        user__isnull=True,
        updated_at__lt=cutoff_date_guest
    ).delete()
    
    # Clean old user carts (keep recent ones)
    abandoned_user_carts = Cart.objects.filter(
        user__isnull=False,
        updated_at__lt=cutoff_date_user
    ).count()
    
    Cart.objects.filter(
        user__isnull=False,
        updated_at__lt=cutoff_date_user
    ).delete()
    
    logger.info(f"Cleaned up {abandoned_guest_carts} guest carts and {abandoned_user_carts} user carts")
    
    return {
        'guest_carts_cleaned': abandoned_guest_carts,
        'user_carts_cleaned': abandoned_user_carts
    } 