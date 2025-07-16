"""
Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Address


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_verified', 'is_active', 'date_joined')
    list_filter = ('is_verified', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Personal Info', {'fields': ('phone', 'date_of_birth', 'is_verified')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'first_name', 'last_name', 'city', 'state', 'is_default')
    list_filter = ('type', 'is_default', 'country', 'state')
    search_fields = ('user__email', 'first_name', 'last_name', 'city')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('User', {'fields': ('user', 'type', 'is_default')}),
        ('Contact Info', {'fields': ('first_name', 'last_name', 'company', 'phone')}),
        ('Address', {'fields': ('address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    readonly_fields = ('created_at', 'updated_at') 