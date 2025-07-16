"""
Django admin interface for orders app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Order, OrderItem, OrderStatusHistory, OrderEvent


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product_name', 'variant_name', 'quantity', 'unit_price', 'total_price')
    readonly_fields = ('product_name', 'variant_name', 'quantity', 'unit_price', 'total_price')


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    fields = ('from_status', 'to_status', 'notes', 'changed_by', 'created_at')
    readonly_fields = ('created_at',)


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    fields = ('event_type', 'message', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'user_info', 'status_badge', 'payment_status_badge',
        'total_amount', 'total_items', 'created_at'
    )
    list_filter = (
        'status', 'payment_status', 'created_at', 'updated_at', 'shipped_at'
    )
    search_fields = (
        'order_number', 'user__email', 'user__first_name', 'user__last_name',
        'shipping_first_name', 'shipping_last_name', 'tracking_number'
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    inlines = [OrderItemInline, OrderStatusHistoryInline, OrderEventInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'payment_status')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax_amount', 'shipping_amount', 'discount_amount', 'total_amount')
        }),
        ('Shipping Address', {
            'fields': (
                'shipping_first_name', 'shipping_last_name', 'shipping_company',
                'shipping_address_line_1', 'shipping_address_line_2',
                'shipping_city', 'shipping_state', 'shipping_postal_code',
                'shipping_country', 'shipping_phone'
            ),
            'classes': ('collapse',)
        }),
        ('Billing Address', {
            'fields': (
                'billing_first_name', 'billing_last_name', 'billing_company',
                'billing_address_line_1', 'billing_address_line_2',
                'billing_city', 'billing_state', 'billing_postal_code',
                'billing_country', 'billing_phone'
            ),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes', 'internal_notes'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('tracking_number', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    
    actions = [
        'mark_as_processing', 'mark_as_confirmed', 'mark_as_shipped',
        'mark_as_delivered', 'mark_as_cancelled'
    ]
    
    def user_info(self, obj):
        user_url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            user_url, obj.user.full_name, obj.user.email
        )
    user_info.short_description = 'Customer'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'confirmed': 'green',
            'shipped': 'purple',
            'delivered': 'darkgreen',
            'cancelled': 'red',
            'refunded': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def payment_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'paid': 'green',
            'failed': 'red',
            'refunded': 'gray',
            'partially_refunded': 'orange'
        }
        color = colors.get(obj.payment_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment'
    
    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Items'
    
    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
        self.message_user(request, f'{queryset.count()} orders marked as processing.')
    mark_as_processing.short_description = 'Mark as Processing'
    
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, f'{queryset.count()} orders marked as confirmed.')
    mark_as_confirmed.short_description = 'Mark as Confirmed'
    
    def mark_as_shipped(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='shipped', shipped_at=timezone.now())
        self.message_user(request, f'{queryset.count()} orders marked as shipped.')
    mark_as_shipped.short_description = 'Mark as Shipped'
    
    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='delivered', delivered_at=timezone.now())
        self.message_user(request, f'{queryset.count()} orders marked as delivered.')
    mark_as_delivered.short_description = 'Mark as Delivered'
    
    def mark_as_cancelled(self, request, queryset):
        for order in queryset:
            order.cancel()
        self.message_user(request, f'{queryset.count()} orders cancelled.')
    mark_as_cancelled.short_description = 'Cancel Orders'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'product_name', 'variant_name', 'quantity',
        'unit_price', 'total_price', 'created_at'
    )
    list_filter = ('created_at',)
    search_fields = ('order__order_number', 'product_name', 'variant_name', 'product_sku')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Order Item Information', {
            'fields': ('order', 'product', 'variant')
        }),
        ('Product Snapshot', {
            'fields': ('product_name', 'variant_name', 'product_sku')
        }),
        ('Pricing', {
            'fields': ('quantity', 'unit_price', 'total_price')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at',)
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Order'


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'from_status', 'to_status', 'changed_by', 'created_at')
    list_filter = ('from_status', 'to_status', 'created_at')
    search_fields = ('order__order_number', 'notes')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Status Change', {
            'fields': ('order', 'from_status', 'to_status', 'changed_by')
        }),
        ('Details', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at',)
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Order'


@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'event_type', 'message', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('order__order_number', 'message')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Event Information', {
            'fields': ('order', 'event_type', 'message')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at',)
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Order' 