"""
Management command to create sample product data for testing.
"""
from django.core.management.base import BaseCommand
from products.models import Category, Brand, Product, ProductAttribute, ProductAttributeValue


class Command(BaseCommand):
    help = 'Create sample product data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample product data...')
        
        # Create Categories
        electronics, created = Category.objects.get_or_create(
            name="Electronics",
            defaults={
                'slug': "electronics",
                'description': "Electronic devices and accessories"
            }
        )
        
        computers, created = Category.objects.get_or_create(
            name="Computers",
            defaults={
                'slug': "computers",
                'description': "Laptops, desktops, and computer accessories",
                'parent': electronics
            }
        )
        
        # Create Brands
        apple, created = Brand.objects.get_or_create(
            name="Apple",
            defaults={
                'slug': "apple",
                'description': "Apple Inc. products",
                'website': "https://apple.com"
            }
        )
        
        dell, created = Brand.objects.get_or_create(
            name="Dell",
            defaults={
                'slug': "dell",
                'description': "Dell Technologies products",
                'website': "https://dell.com"
            }
        )
        
        # Create Products
        products_data = [
            {
                'name': "MacBook Pro 16-inch",
                'description': "Latest MacBook Pro with M3 chip, perfect for professionals",
                'price': 2999.00,
                'compare_at_price': 3299.00,
                'sku': "MBP-16-M3-512",
                'stock_quantity': 15,
                'category': computers,
                'brand': apple,
                'is_featured': True,
                'status': 'active'
            },
            {
                'name': "Dell XPS 13",
                'description': "Ultra-portable laptop with stunning display",
                'price': 1299.00,
                'compare_at_price': 1499.00,
                'sku': "DELL-XPS13-512",
                'stock_quantity': 8,
                'category': computers,
                'brand': dell,
                'is_featured': True,
                'status': 'active'
            },
            {
                'name': "iPhone 15 Pro",
                'description': "Latest iPhone with A17 Pro chip",
                'price': 999.00,
                'sku': "IPHONE-15-PRO-128",
                'stock_quantity': 25,
                'category': electronics,
                'brand': apple,
                'is_featured': True,
                'status': 'active'
            },
            {
                'name': "iPad Air",
                'description': "Powerful, colorful, and versatile",
                'price': 599.00,
                'sku': "IPAD-AIR-64",
                'stock_quantity': 12,
                'category': electronics,
                'brand': apple,
                'status': 'active'
            },
            {
                'name': "Dell Monitor 27-inch",
                'description': "4K UHD monitor for professional use",
                'price': 399.00,
                'sku': "DELL-MON-27-4K",
                'stock_quantity': 20,
                'category': computers,
                'brand': dell,
                'status': 'active'
            }
        ]
        
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                sku=product_data['sku'],
                defaults=product_data
            )
            if created:
                self.stdout.write(f'Created product: {product.name}')
            else:
                self.stdout.write(f'Product already exists: {product.name}')
        
        # Create Product Attributes
        color_attr, created = ProductAttribute.objects.get_or_create(
            name="color",
            defaults={
                'display_name': "Color",
                'type': "choice",
                'required': True
            }
        )
        
        storage_attr, created = ProductAttribute.objects.get_or_create(
            name="storage",
            defaults={
                'display_name': "Storage Capacity",
                'type': "choice",
                'required': True
            }
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample data! Total products: {Product.objects.count()}'
            )
        ) 