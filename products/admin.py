"""
Django admin interface for products app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category, Brand, Product, ProductImage, 
    ProductAttribute, ProductAttributeValue, ProductVariant
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'sort_order')


class ProductAttributeValueInline(admin.TabularInline):
    model = ProductAttributeValue
    extra = 1
    fields = ('attribute', 'value')


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('name', 'sku', 'price', 'stock_quantity', 'is_active', 'sort_order')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_active', 'sort_order', 'created_at')
    list_filter = ('is_active', 'parent', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('sort_order', 'name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'parent')
        }),
        ('Settings', {
            'fields': ('is_active', 'sort_order')
        }),
        ('Media', {
            'fields': ('image',)
        }),
    )


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'website')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
        ('Media', {
            'fields': ('logo',)
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'sku', 'category', 'brand', 'price', 'stock_status', 
        'status', 'is_featured', 'created_at'
    )
    list_filter = (
        'status', 'is_featured', 'is_digital', 'track_inventory',
        'category', 'brand', 'created_at'
    )
    search_fields = ('name', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    inlines = [ProductImageInline, ProductAttributeValueInline, ProductVariantInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'short_description', 'sku')
        }),
        ('Classification', {
            'fields': ('category', 'brand')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price', 'cost_price')
        }),
        ('Inventory', {
            'fields': ('track_inventory', 'stock_quantity', 'low_stock_threshold')
        }),
        ('Physical Properties', {
            'fields': ('weight', 'dimensions_length', 'dimensions_width', 'dimensions_height')
        }),
        ('SEO & Meta', {
            'fields': ('meta_title', 'meta_description')
        }),
        ('Status & Visibility', {
            'fields': ('status', 'is_featured', 'is_digital', 'requires_shipping')
        }),
        ('Publishing', {
            'fields': ('published_at',)
        }),
    )
    
    def stock_status(self, obj):
        if not obj.track_inventory:
            return format_html('<span style="color: blue;">Not Tracked</span>')
        elif obj.stock_quantity <= 0:
            return format_html('<span style="color: red;">Out of Stock</span>')
        elif obj.is_low_stock:
            return format_html('<span style="color: orange;">Low Stock ({})</span>', obj.stock_quantity)
        else:
            return format_html('<span style="color: green;">In Stock ({})</span>', obj.stock_quantity)
    
    stock_status.short_description = 'Stock Status'
    
    actions = ['mark_as_featured', 'unmark_as_featured', 'activate_products', 'deactivate_products']
    
    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f'{queryset.count()} products marked as featured.')
    mark_as_featured.short_description = 'Mark selected products as featured'
    
    def unmark_as_featured(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, f'{queryset.count()} products unmarked as featured.')
    unmark_as_featured.short_description = 'Unmark selected products as featured'
    
    def activate_products(self, request, queryset):
        queryset.update(status='active')
        self.message_user(request, f'{queryset.count()} products activated.')
    activate_products.short_description = 'Activate selected products'
    
    def deactivate_products(self, request, queryset):
        queryset.update(status='inactive')
        self.message_user(request, f'{queryset.count()} products deactivated.')
    deactivate_products.short_description = 'Deactivate selected products'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'alt_text', 'is_primary', 'sort_order', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('product__name', 'alt_text')
    ordering = ('product', 'sort_order', 'created_at')


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'type', 'required', 'created_at')
    list_filter = ('type', 'required', 'created_at')
    search_fields = ('name', 'display_name')
    ordering = ('display_name',)


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ('product', 'attribute', 'value', 'created_at')
    list_filter = ('attribute', 'created_at')
    search_fields = ('product__name', 'attribute__display_name', 'value')
    ordering = ('product', 'attribute')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        'product', 'name', 'sku', 'effective_price', 'stock_quantity',
        'is_active', 'created_at'
    )
    list_filter = ('is_active', 'created_at')
    search_fields = ('product__name', 'name', 'sku')
    ordering = ('product', 'sort_order', 'name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('product', 'name', 'sku')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity',)
        }),
        ('Physical Properties', {
            'fields': ('weight',)
        }),
        ('Settings', {
            'fields': ('is_active', 'sort_order')
        }),
    )
    
    def effective_price(self, obj):
        return f"${obj.effective_price}"
    effective_price.short_description = 'Effective Price' 