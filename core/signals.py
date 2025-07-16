"""
Django signals for automatic audit logging.
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from threading import local
import json

from .models import AuditLog
from products.models import Product, ProductVariant
from orders.models import Order

User = get_user_model()

# Thread-local storage for current user
_thread_locals = local()


def get_current_user():
    """Get the current user from thread-local storage."""
    return getattr(_thread_locals, 'user', None)


def set_current_user(user):
    """Set the current user in thread-local storage."""
    _thread_locals.user = user


class AuditMiddleware:
    """Middleware to capture current user for audit logging."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set current user in thread-local storage
        if hasattr(request, 'user') and request.user.is_authenticated:
            set_current_user(request.user)
        else:
            set_current_user(None)
        
        response = self.get_response(request)
        
        # Clear user from thread-local storage
        set_current_user(None)
        
        return response


def create_audit_log(model_name, object_id, action, field_name=None, old_value=None, new_value=None, metadata=None):
    """Helper function to create audit log entries."""
    try:
        AuditLog.objects.create(
            model_name=model_name,
            object_id=str(object_id),
            action=action,
            field_name=field_name or '',
            old_value=str(old_value) if old_value is not None else '',
            new_value=str(new_value) if new_value is not None else '',
            user=get_current_user(),
            metadata=metadata or {}
        )
    except Exception as e:
        import logging
        logger = logging.getLogger('ecommerce')
        logger.error(f"Failed to create audit log: {str(e)}")


@receiver(post_save, sender=Product)
def audit_product_changes(sender, instance, created, **kwargs):
    """Audit product creation and updates."""
    if created:
        create_audit_log(
            model_name='Product',
            object_id=instance.id,
            action='create',
            metadata={
                'product_name': instance.name,
                'sku': instance.sku,
                'category': instance.category.name if instance.category else None,
                'price': str(instance.price)
            }
        )
    else:
        create_audit_log(
            model_name='Product',
            object_id=instance.id,
            action='update',
            metadata={
                'product_name': instance.name,
                'sku': instance.sku
            }
        )


@receiver(pre_save, sender=Product)
def track_product_stock_changes(sender, instance, **kwargs):
    """Track product stock changes."""
    if instance.pk:  # Only for existing products
        try:
            old_instance = Product.objects.get(pk=instance.pk)
            if old_instance.stock_quantity != instance.stock_quantity:
                create_audit_log(
                    model_name='Product',
                    object_id=instance.id,
                    action='stock_change',
                    field_name='stock_quantity',
                    old_value=old_instance.stock_quantity,
                    new_value=instance.stock_quantity,
                    metadata={
                        'product_name': instance.name,
                        'sku': instance.sku,
                        'difference': instance.stock_quantity - old_instance.stock_quantity
                    }
                )
        except Product.DoesNotExist:
            pass


@receiver(pre_save, sender=ProductVariant)
def track_variant_stock_changes(sender, instance, **kwargs):
    """Track product variant stock changes."""
    if instance.pk:  # Only for existing variants
        try:
            old_instance = ProductVariant.objects.get(pk=instance.pk)
            if old_instance.stock_quantity != instance.stock_quantity:
                create_audit_log(
                    model_name='ProductVariant',
                    object_id=instance.id,
                    action='stock_change',
                    field_name='stock_quantity',
                    old_value=old_instance.stock_quantity,
                    new_value=instance.stock_quantity,
                    metadata={
                        'product_name': instance.product.name,
                        'variant_name': instance.name,
                        'sku': instance.sku,
                        'difference': instance.stock_quantity - old_instance.stock_quantity
                    }
                )
        except ProductVariant.DoesNotExist:
            pass


@receiver(post_save, sender=Order)
def audit_order_changes(sender, instance, created, **kwargs):
    """Audit order creation and status changes."""
    if created:
        create_audit_log(
            model_name='Order',
            object_id=instance.id,
            action='create',
            metadata={
                'order_number': instance.order_number,
                'user_id': instance.user.id,
                'user_email': instance.user.email,
                'total_amount': str(instance.total_amount),
                'status': instance.status
            }
        )


@receiver(pre_save, sender=Order)
def track_order_status_changes(sender, instance, **kwargs):
    """Track order status changes."""
    if instance.pk:  # Only for existing orders
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                create_audit_log(
                    model_name='Order',
                    object_id=instance.id,
                    action='status_change',
                    field_name='status',
                    old_value=old_instance.status,
                    new_value=instance.status,
                    metadata={
                        'order_number': instance.order_number,
                        'user_id': instance.user.id,
                        'user_email': instance.user.email
                    }
                )
            
            if old_instance.payment_status != instance.payment_status:
                create_audit_log(
                    model_name='Order',
                    object_id=instance.id,
                    action='status_change',
                    field_name='payment_status',
                    old_value=old_instance.payment_status,
                    new_value=instance.payment_status,
                    metadata={
                        'order_number': instance.order_number,
                        'user_id': instance.user.id,
                        'user_email': instance.user.email
                    }
                )
        except Order.DoesNotExist:
            pass


@receiver(post_delete, sender=Product)
def audit_product_deletion(sender, instance, **kwargs):
    """Audit product deletion."""
    create_audit_log(
        model_name='Product',
        object_id=instance.id,
        action='delete',
        metadata={
            'product_name': instance.name,
            'sku': instance.sku,
            'category': instance.category.name if instance.category else None
        }
    )


@receiver(post_delete, sender=Order)
def audit_order_deletion(sender, instance, **kwargs):
    """Audit order deletion."""
    create_audit_log(
        model_name='Order',
        object_id=instance.id,
        action='delete',
        metadata={
            'order_number': instance.order_number,
            'user_id': instance.user.id,
            'user_email': instance.user.email,
            'total_amount': str(instance.total_amount)
        }
    ) 