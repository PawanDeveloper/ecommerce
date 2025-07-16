"""
Cart models for shopping cart management.
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class Cart(models.Model):
    """
    Shopping cart model for authenticated and guest users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='cart'
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carts'
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Guest Cart {self.id}"

    @property
    def total_items(self):
        """Get total number of items in cart."""
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        """Calculate cart subtotal."""
        return sum(item.total_price for item in self.items.all())

    @property
    def total(self):
        """Calculate cart total (same as subtotal for now, can add taxes/shipping later)."""
        return self.subtotal

    def clear(self):
        """Clear all items from cart."""
        self.items.all().delete()

    def merge_with_user_cart(self, user_cart):
        """Merge this cart with user's existing cart."""
        for item in self.items.all():
            user_cart_item, created = user_cart.items.get_or_create(
                product=item.product,
                variant=item.variant,
                defaults={'quantity': item.quantity}
            )
            if not created:
                user_cart_item.quantity += item.quantity
                user_cart_item.save()
        
        # Delete this cart after merging
        self.delete()


class CartItem(models.Model):
    """
    Cart item model representing products in a cart.
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey(
        'products.ProductVariant', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart_items'
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ['cart', 'product', 'variant']

    def __str__(self):
        if self.variant:
            return f"{self.product.name} - {self.variant.name} (x{self.quantity})"
        return f"{self.product.name} (x{self.quantity})"

    @property
    def unit_price(self):
        """Get the unit price for this item."""
        if self.variant:
            return self.variant.effective_price
        return self.product.price

    @property
    def total_price(self):
        """Calculate total price for this cart item."""
        return self.unit_price * self.quantity

    def clean(self):
        """Validate cart item."""
        from django.core.exceptions import ValidationError
        
        # Check if product is active
        if self.product.status != 'active':
            raise ValidationError("Product is not available for purchase.")
        
        # Check stock availability
        if self.variant:
            if not self.variant.is_in_stock:
                raise ValidationError("Product variant is out of stock.")
            if self.quantity > self.variant.stock_quantity:
                raise ValidationError(
                    f"Only {self.variant.stock_quantity} items available in stock."
                )
        else:
            if not self.product.is_in_stock:
                raise ValidationError("Product is out of stock.")
            if self.product.track_inventory and self.quantity > self.product.stock_quantity:
                raise ValidationError(
                    f"Only {self.product.stock_quantity} items available in stock."
                )

    def save(self, *args, **kwargs):
        """Save cart item with validation."""
        self.full_clean()
        super().save(*args, **kwargs)
        # Update cart's updated_at timestamp
        self.cart.save(update_fields=['updated_at'])


class SavedItem(models.Model):
    """
    Saved items model for wishlist functionality.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='saved_items'
    )
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey(
        'products.ProductVariant', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'saved_items'
        verbose_name = 'Saved Item'
        verbose_name_plural = 'Saved Items'
        unique_together = ['user', 'product', 'variant']

    def __str__(self):
        if self.variant:
            return f"{self.user.email} - {self.product.name} ({self.variant.name})"
        return f"{self.user.email} - {self.product.name}" 