"""
GraphQL schema for products app.
"""
import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene import relay
from django_filters import FilterSet, CharFilter, NumberFilter, BooleanFilter

from .models import Product, Category, Brand, ProductImage, ProductVariant, ProductAttribute, ProductAttributeValue


class CategoryType(DjangoObjectType):
    """
    GraphQL type for Category model.
    """
    is_parent = graphene.Boolean()
    
    class Meta:
        model = Category
        fields = '__all__'
        interfaces = (relay.Node,)
        
    def resolve_is_parent(self, info):
        return self.is_parent


class BrandType(DjangoObjectType):
    """
    GraphQL type for Brand model.
    """
    class Meta:
        model = Brand
        fields = '__all__'
        interfaces = (relay.Node,)


class ProductImageType(DjangoObjectType):
    """
    GraphQL type for ProductImage model.
    """
    class Meta:
        model = ProductImage
        fields = '__all__'


class ProductAttributeDefinitionType(DjangoObjectType):
    """
    GraphQL type for ProductAttribute model.
    """
    class Meta:
        model = ProductAttribute
        fields = '__all__'


class ProductAttributeValueType(DjangoObjectType):
    """
    GraphQL type for ProductAttributeValue model.
    """
    class Meta:
        model = ProductAttributeValue
        fields = '__all__'


class ProductVariantType(DjangoObjectType):
    """
    GraphQL type for ProductVariant model.
    """
    effective_price = graphene.Decimal()
    is_in_stock = graphene.Boolean()
    
    class Meta:
        model = ProductVariant
        fields = '__all__'
        
    def resolve_effective_price(self, info):
        return self.effective_price
        
    def resolve_is_in_stock(self, info):
        return self.is_in_stock


class ProductType(DjangoObjectType):
    """
    GraphQL type for Product model.
    """
    is_in_stock = graphene.Boolean()
    is_low_stock = graphene.Boolean()
    discount_percentage = graphene.Float()
    images = graphene.List(ProductImageType)
    variants = graphene.List(ProductVariantType)
    attributes = graphene.List(ProductAttributeValueType)
    
    class Meta:
        model = Product
        fields = '__all__'
        interfaces = (relay.Node,)
        
    def resolve_is_in_stock(self, info):
        return self.is_in_stock
        
    def resolve_is_low_stock(self, info):
        return self.is_low_stock
        
    def resolve_discount_percentage(self, info):
        return self.discount_percentage
        
    def resolve_images(self, info):
        return self.images.all()
        
    def resolve_variants(self, info):
        return self.variants.filter(is_active=True)
        
    def resolve_attributes(self, info):
        return self.attributes.all()


class ProductFilter(FilterSet):
    """
    Filter set for Product model with advanced filtering options.
    """
    # Category filtering
    category = CharFilter(field_name='category__slug', lookup_expr='exact')
    category_name = CharFilter(field_name='category__name', lookup_expr='icontains')
    
    # Brand filtering
    brand = CharFilter(field_name='brand__slug', lookup_expr='exact')
    brand_name = CharFilter(field_name='brand__name', lookup_expr='icontains')
    
    # Price range filtering
    price_min = NumberFilter(field_name='price', lookup_expr='gte')
    price_max = NumberFilter(field_name='price', lookup_expr='lte')
    
    # Stock filtering
    in_stock = BooleanFilter(method='filter_in_stock')
    
    # Search functionality
    search = CharFilter(method='filter_search')
    
    # Status filtering
    is_featured = BooleanFilter(field_name='is_featured')
    
    class Meta:
        model = Product
        fields = ['status', 'is_featured']

    def filter_in_stock(self, queryset, name, value):
        """Filter products based on stock availability."""
        from django.db import models
        if value:
            # Products either don't track inventory or have stock > 0
            return queryset.filter(
                models.Q(track_inventory=False) | 
                models.Q(track_inventory=True, stock_quantity__gt=0)
            )
        return queryset

    def filter_search(self, queryset, name, value):
        """Search in product name, description, and SKU."""
        from django.db import models
        return queryset.filter(
            models.Q(name__icontains=value) |
            models.Q(description__icontains=value) |
            models.Q(sku__icontains=value)
        )


class ProductConnection(relay.Connection):
    """
    Relay connection for paginated products.
    """
    class Meta:
        node = ProductType

    total_count = graphene.Int()

    def resolve_total_count(self, info):
        return self.length


class ProductsQuery(graphene.ObjectType):
    """
    Queries for products app.
    """
    # Single product queries
    product = relay.Node.Field(ProductType)
    product_by_slug = graphene.Field(ProductType, slug=graphene.String(required=True))
    
    # List queries with pagination and filtering
    products = DjangoFilterConnectionField(
        ProductType,
        filterset_class=ProductFilter,
        description="Get products with pagination and filtering"
    )
    
    # Category queries
    categories = graphene.List(CategoryType)
    category = graphene.Field(CategoryType, slug=graphene.String(required=True))
    
    # Brand queries
    brands = graphene.List(BrandType)
    brand = graphene.Field(BrandType, slug=graphene.String(required=True))
    
    # Featured products
    featured_products = graphene.List(ProductType, first=graphene.Int())

    def resolve_product_by_slug(self, info, slug):
        """Get product by slug."""
        try:
            return Product.objects.select_related('category', 'brand').get(
                slug=slug, 
                status='active'
            )
        except Product.DoesNotExist:
            return None

    def resolve_products(self, info, **kwargs):
        """Get products with filtering applied."""
        return Product.objects.select_related('category', 'brand').filter(
            status='active'
        ).order_by('-created_at')

    def resolve_categories(self, info):
        """Get all active categories."""
        return Category.objects.filter(is_active=True).order_by('sort_order', 'name')

    def resolve_category(self, info, slug):
        """Get category by slug."""
        try:
            return Category.objects.get(slug=slug, is_active=True)
        except Category.DoesNotExist:
            return None

    def resolve_brands(self, info):
        """Get all active brands."""
        return Brand.objects.filter(is_active=True).order_by('name')

    def resolve_brand(self, info, slug):
        """Get brand by slug."""
        try:
            return Brand.objects.get(slug=slug, is_active=True)
        except Brand.DoesNotExist:
            return None

    def resolve_featured_products(self, info, first=None):
        """Get featured products."""
        queryset = Product.objects.select_related('category', 'brand').filter(
            status='active',
            is_featured=True
        ).order_by('-created_at')
        
        if first:
            queryset = queryset[:first]
            
        return queryset 