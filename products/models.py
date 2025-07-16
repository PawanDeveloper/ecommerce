"""
Product models for e-commerce catalog management.
"""
from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from decimal import Decimal


class Category(models.Model):
    """
    Product category model with hierarchical structure.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children'
    )
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_parent(self):
        return self.children.exists()


class Brand(models.Model):
    """
    Product brand model.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_brands'
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """
    Main product model.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('discontinued', 'Discontinued'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=500, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    sku = models.CharField(max_length=100, unique=True)
    
    # Pricing
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    compare_at_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Original price for discount calculation"
    )
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Cost price for profit calculation"
    )
    
    # Inventory
    track_inventory = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    
    # Physical attributes
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    dimensions_length = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    dimensions_width = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    dimensions_height = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # SEO and metadata
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    
    # Status and visibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    is_digital = models.BooleanField(default=False)
    requires_shipping = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['sku']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['brand']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_in_stock(self):
        """Check if product is in stock."""
        if not self.track_inventory:
            return True
        return self.stock_quantity > 0

    @property
    def is_low_stock(self):
        """Check if product stock is below threshold."""
        if not self.track_inventory:
            return False
        return self.stock_quantity <= self.low_stock_threshold

    @property
    def discount_percentage(self):
        """Calculate discount percentage if compare_at_price is set."""
        if self.compare_at_price and self.compare_at_price > self.price:
            return round(((self.compare_at_price - self.price) / self.compare_at_price) * 100, 2)
        return 0

    def reduce_stock(self, quantity):
        """Reduce stock quantity safely."""
        if self.track_inventory:
            if self.stock_quantity >= quantity:
                self.stock_quantity -= quantity
                self.save(update_fields=['stock_quantity'])
            else:
                raise ValueError("Insufficient stock")

    def increase_stock(self, quantity):
        """Increase stock quantity."""
        if self.track_inventory:
            self.stock_quantity += quantity
            self.save(update_fields=['stock_quantity'])


class ProductImage(models.Model):
    """
    Product image model for multiple images per product.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_images'
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['sort_order', 'created_at']

    def __str__(self):
        return f"{self.product.name} - Image {self.id}"


class ProductAttribute(models.Model):
    """
    Product attribute types (e.g., Color, Size, Material).
    """
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),
            ('number', 'Number'),
            ('boolean', 'Boolean'),
            ('date', 'Date'),
            ('choice', 'Choice'),
        ],
        default='text'
    )
    required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_attributes'
        verbose_name = 'Product Attribute'
        verbose_name_plural = 'Product Attributes'

    def __str__(self):
        return self.display_name


class ProductAttributeValue(models.Model):
    """
    Product attribute values for specific products.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='attributes')
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE)
    value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_attribute_values'
        verbose_name = 'Product Attribute Value'
        verbose_name_plural = 'Product Attribute Values'
        unique_together = ['product', 'attribute']

    def __str__(self):
        return f"{self.product.name} - {self.attribute.display_name}: {self.value}"


class ProductVariant(models.Model):
    """
    Product variants for products with multiple options (e.g., size, color).
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True)
    
    # Pricing (can override product pricing)
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Leave blank to use product price"
    )
    compare_at_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    # Inventory
    stock_quantity = models.PositiveIntegerField(default=0)
    
    # Physical attributes
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_variants'
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def effective_price(self):
        """Get the effective price (variant price or product price)."""
        return self.price or self.product.price

    @property
    def is_in_stock(self):
        """Check if variant is in stock."""
        return self.stock_quantity > 0

    def reduce_stock(self, quantity):
        """Reduce variant stock quantity safely."""
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.save(update_fields=['stock_quantity'])
        else:
            raise ValueError("Insufficient variant stock")

    def increase_stock(self, quantity):
        """Increase variant stock quantity."""
        self.stock_quantity += quantity
        self.save(update_fields=['stock_quantity']) 