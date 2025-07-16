"""
Django admin interface for cart app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Cart, CartItem, SavedItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ('product', 'variant', 'quantity', 'unit_price', 'total_price')
    readonly_fields = ('unit_price', 'total_price')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'total_items', 'subtotal', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'user__username', 'session_key')
    ordering = ('-updated_at',)
    date_hierarchy = 'created_at'
    
    inlines = [CartItemInline]
    
    fieldsets = (
        ('Cart Information', {
            'fields': ('user', 'session_key')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def user_display(self, obj):
        if obj.user:
            return format_html('<strong>{}</strong><br>{}', obj.user.full_name, obj.user.email)
        return format_html('<span style="color: gray;">Guest Cart</span>')
    user_display.short_description = 'User'
    
    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Items'
    
    def subtotal(self, obj):
        return f"${obj.subtotal}"
    subtotal.short_description = 'Subtotal'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        'cart_user', 'product', 'variant', 'quantity', 
        'unit_price', 'total_price', 'created_at'
    )
    list_filter = ('created_at', 'updated_at')
    search_fields = ('cart__user__email', 'product__name', 'variant__name')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Cart Item Information', {
            'fields': ('cart', 'product', 'variant', 'quantity')
        }),
        ('Pricing', {
            'fields': ('unit_price', 'total_price'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('unit_price', 'total_price', 'created_at', 'updated_at')
    
    def cart_user(self, obj):
        if obj.cart.user:
            return obj.cart.user.email
        return 'Guest'
    cart_user.short_description = 'User'


@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'variant', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'product__name', 'variant__name')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Saved Item Information', {
            'fields': ('user', 'product', 'variant')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at',) 