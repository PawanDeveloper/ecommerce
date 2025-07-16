"""
Order models for order management and tracking.
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class Order(models.Model):
    """
    Order model for tracking customer orders.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    # Order identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=50, unique=True, blank=True)
    
    # Customer information
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='orders'
    )
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='pending'
    )
    
    # Pricing
    subtotal = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    shipping_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Shipping information
    shipping_first_name = models.CharField(max_length=30)
    shipping_last_name = models.CharField(max_length=30)
    shipping_company = models.CharField(max_length=100, blank=True)
    shipping_address_line_1 = models.CharField(max_length=255)
    shipping_address_line_2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)
    shipping_phone = models.CharField(max_length=20, blank=True)
    
    # Billing information
    billing_first_name = models.CharField(max_length=30)
    billing_last_name = models.CharField(max_length=30)
    billing_company = models.CharField(max_length=100, blank=True)
    billing_address_line_1 = models.CharField(max_length=255)
    billing_address_line_2 = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=100)
    billing_state = models.CharField(max_length=100)
    billing_postal_code = models.CharField(max_length=20)
    billing_country = models.CharField(max_length=100)
    billing_phone = models.CharField(max_length=20, blank=True)
    
    # Additional information
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True, help_text="Internal notes not visible to customer")
    
    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Order #{self.order_number}"

    def save(self, *args, **kwargs):
        """Generate order number if not set."""
        if not self.order_number:
            # Generate order number based on timestamp and random component
            import time
            import random
            timestamp = str(int(time.time()))[-6:]
            random_part = str(random.randint(100, 999))
            self.order_number = f"ORD-{timestamp}{random_part}"
        super().save(*args, **kwargs)

    @property
    def total_items(self):
        """Get total number of items in order."""
        return sum(item.quantity for item in self.items.all())

    @property
    def shipping_address(self):
        """Get formatted shipping address."""
        address_parts = [
            self.shipping_address_line_1,
            self.shipping_address_line_2,
            f"{self.shipping_city}, {self.shipping_state} {self.shipping_postal_code}",
            self.shipping_country
        ]
        return '\n'.join(filter(None, address_parts))

    @property
    def billing_address(self):
        """Get formatted billing address."""
        address_parts = [
            self.billing_address_line_1,
            self.billing_address_line_2,
            f"{self.billing_city}, {self.billing_state} {self.billing_postal_code}",
            self.billing_country
        ]
        return '\n'.join(filter(None, address_parts))

    def can_be_cancelled(self):
        """Check if order can be cancelled."""
        return self.status in ['pending', 'processing', 'confirmed']

    def cancel(self):
        """Cancel the order."""
        if self.can_be_cancelled():
            self.status = 'cancelled'
            self.save(update_fields=['status', 'updated_at'])
            
            # Restore stock for all items
            for item in self.items.all():
                if item.variant:
                    item.variant.increase_stock(item.quantity)
                else:
                    item.product.increase_stock(item.quantity)


class OrderItem(models.Model):
    """
    Order item model representing products in an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    variant = models.ForeignKey(
        'products.ProductVariant', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True
    )
    
    # Snapshot data at time of order
    product_name = models.CharField(max_length=200)
    variant_name = models.CharField(max_length=200, blank=True)
    product_sku = models.CharField(max_length=100)
    
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_items'
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        if self.variant_name:
            return f"{self.product_name} - {self.variant_name} (x{self.quantity})"
        return f"{self.product_name} (x{self.quantity})"

    def save(self, *args, **kwargs):
        """Calculate total price before saving."""
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """
    Order status history for tracking status changes.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_status_history'
        verbose_name = 'Order Status History'
        verbose_name_plural = 'Order Status Histories'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order.order_number}: {self.from_status} → {self.to_status}"


class OrderEvent(models.Model):
    """
    Order events for tracking important order activities.
    """
    EVENT_TYPES = [
        ('created', 'Order Created'),
        ('payment_received', 'Payment Received'),
        ('payment_failed', 'Payment Failed'),
        ('confirmed', 'Order Confirmed'),
        ('confirmation_sent', 'Confirmation Sent'),
        ('shipped', 'Order Shipped'),
        ('delivered', 'Order Delivered'),
        ('cancelled', 'Order Cancelled'),
        ('refunded', 'Order Refunded'),
        ('note_added', 'Note Added'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_events'
        verbose_name = 'Order Event'
        verbose_name_plural = 'Order Events'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order.order_number}: {self.get_event_type_display()}" 