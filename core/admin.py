"""
Django admin interface for core app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'timestamp', 'model_name', 'object_id', 'action_badge',
        'field_name', 'user_info', 'changes'
    )
    list_filter = ('model_name', 'action', 'timestamp')
    search_fields = ('model_name', 'object_id', 'field_name', 'user__email')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Audit Information', {
            'fields': ('model_name', 'object_id', 'action', 'field_name', 'user')
        }),
        ('Changes', {
            'fields': ('old_value', 'new_value')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('timestamp',)
    
    def action_badge(self, obj):
        colors = {
            'create': 'green',
            'update': 'blue',
            'delete': 'red',
            'stock_change': 'orange',
            'status_change': 'purple'
        }
        color = colors.get(obj.action, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_action_display()
        )
    action_badge.short_description = 'Action'
    
    def user_info(self, obj):
        if obj.user:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.user.full_name, obj.user.email
            )
        return format_html('<span style="color: gray;">System</span>')
    user_info.short_description = 'User'
    
    def changes(self, obj):
        if obj.field_name and obj.old_value and obj.new_value:
            return format_html(
                '<strong>{}:</strong> {} → {}',
                obj.field_name, 
                obj.old_value[:30] + '...' if len(obj.old_value) > 30 else obj.old_value,
                obj.new_value[:30] + '...' if len(obj.new_value) > 30 else obj.new_value
            )
        return '-'
    changes.short_description = 'Changes'
    
    def has_add_permission(self, request):
        """Audit logs should not be manually created."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Audit logs should not be manually edited."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes."""
        return request.user.is_superuser 