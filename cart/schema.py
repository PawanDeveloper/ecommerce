"""
GraphQL schema for cart app.
"""
import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

from .models import Cart, CartItem
from products.models import Product, ProductVariant


class CartItemType(DjangoObjectType):
    """
    GraphQL type for CartItem model.
    """
    unit_price = graphene.Decimal()
    total_price = graphene.Decimal()
    
    class Meta:
        model = CartItem
        fields = '__all__'
        
    def resolve_unit_price(self, info):
        return self.unit_price
        
    def resolve_total_price(self, info):
        return self.total_price


class CartType(DjangoObjectType):
    """
    GraphQL type for Cart model.
    """
    total_items = graphene.Int()
    subtotal = graphene.Decimal()
    total = graphene.Decimal()
    
    class Meta:
        model = Cart
        fields = '__all__'
        
    def resolve_total_items(self, info):
        return self.total_items
        
    def resolve_subtotal(self, info):
        from decimal import Decimal
        subtotal = self.subtotal
        return Decimal('0.00') if subtotal == 0 else subtotal
        
    def resolve_total(self, info):
        from decimal import Decimal
        total = self.total
        return Decimal('0.00') if total == 0 else total


class AddToCartMutation(graphene.Mutation):
    """
    Mutation to add a product to cart.
    """
    class Arguments:
        product_id = graphene.ID(required=True)
        variant_id = graphene.ID()
        quantity = graphene.Int(default_value=1)

    cart = graphene.Field(CartType)
    cart_item = graphene.Field(CartItemType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @login_required
    def mutate(self, info, product_id, quantity=1, variant_id=None):
        try:
            user = info.context.user
            
            # Get or create user's cart
            cart, created = Cart.objects.get_or_create(user=user)
            
            # Get product
            try:
                product = Product.objects.get(id=product_id, status='active')
            except Product.DoesNotExist:
                return AddToCartMutation(
                    success=False,
                    errors=['Product not found or not available']
                )
            
            # Get variant if specified
            variant = None
            if variant_id:
                try:
                    variant = ProductVariant.objects.get(
                        id=variant_id, 
                        product=product,
                        is_active=True
                    )
                except ProductVariant.DoesNotExist:
                    return AddToCartMutation(
                        success=False,
                        errors=['Product variant not found']
                    )
            
            # Check stock availability
            if variant:
                if not variant.is_in_stock:
                    return AddToCartMutation(
                        success=False,
                        errors=['Product variant is out of stock']
                    )
                if quantity > variant.stock_quantity:
                    return AddToCartMutation(
                        success=False,
                        errors=[f'Only {variant.stock_quantity} items available']
                    )
            else:
                if not product.is_in_stock:
                    return AddToCartMutation(
                        success=False,
                        errors=['Product is out of stock']
                    )
                if product.track_inventory and quantity > product.stock_quantity:
                    return AddToCartMutation(
                        success=False,
                        errors=[f'Only {product.stock_quantity} items available']
                    )
            
            # Add to cart or update existing item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                variant=variant,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            return AddToCartMutation(
                cart=cart,
                cart_item=cart_item,
                success=True,
                errors=[]
            )

        except Exception as e:
            return AddToCartMutation(
                success=False,
                errors=[str(e)]
            )


class UpdateCartItemMutation(graphene.Mutation):
    """
    Mutation to update cart item quantity.
    """
    class Arguments:
        product_id = graphene.ID(required=True)
        variant_id = graphene.ID()
        quantity = graphene.Int(required=True)

    cart = graphene.Field(CartType)
    cart_item = graphene.Field(CartItemType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @login_required
    def mutate(self, info, product_id, quantity, variant_id=None):
        try:
            user = info.context.user
            
            # Get user's cart
            try:
                cart = user.cart
            except Cart.DoesNotExist:
                return UpdateCartItemMutation(
                    success=False,
                    errors=['Cart not found']
                )
            
            # Get cart item
            try:
                cart_item = cart.items.get(
                    product_id=product_id,
                    variant_id=variant_id
                )
            except CartItem.DoesNotExist:
                return UpdateCartItemMutation(
                    success=False,
                    errors=['Item not found in cart']
                )
            
            if quantity <= 0:
                cart_item.delete()
                cart_item = None
            else:
                # Check stock availability
                if cart_item.variant:
                    if quantity > cart_item.variant.stock_quantity:
                        return UpdateCartItemMutation(
                            success=False,
                            errors=[f'Only {cart_item.variant.stock_quantity} items available']
                        )
                else:
                    if cart_item.product.track_inventory and quantity > cart_item.product.stock_quantity:
                        return UpdateCartItemMutation(
                            success=False,
                            errors=[f'Only {cart_item.product.stock_quantity} items available']
                        )
                
                cart_item.quantity = quantity
                cart_item.save()

            return UpdateCartItemMutation(
                cart=cart,
                cart_item=cart_item,
                success=True,
                errors=[]
            )

        except Exception as e:
            return UpdateCartItemMutation(
                success=False,
                errors=[str(e)]
            )


class RemoveFromCartMutation(graphene.Mutation):
    """
    Mutation to remove an item from cart.
    """
    class Arguments:
        product_id = graphene.ID(required=True)
        variant_id = graphene.ID()

    cart = graphene.Field(CartType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @login_required
    def mutate(self, info, product_id, variant_id=None):
        try:
            user = info.context.user
            
            # Get user's cart
            try:
                cart = user.cart
            except Cart.DoesNotExist:
                return RemoveFromCartMutation(
                    success=False,
                    errors=['Cart not found']
                )
            
            # Get and delete cart item
            try:
                cart_item = cart.items.get(
                    product_id=product_id,
                    variant_id=variant_id
                )
                cart_item.delete()
            except CartItem.DoesNotExist:
                return RemoveFromCartMutation(
                    success=False,
                    errors=['Item not found in cart']
                )

            return RemoveFromCartMutation(
                cart=cart,
                success=True,
                errors=[]
            )

        except Exception as e:
            return RemoveFromCartMutation(
                success=False,
                errors=[str(e)]
            )


class ClearCartMutation(graphene.Mutation):
    """
    Mutation to clear all items from cart.
    """
    cart = graphene.Field(CartType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @login_required
    def mutate(self, info):
        try:
            user = info.context.user
            cart = user.cart
            cart.clear()
            return ClearCartMutation(
                cart=cart,
                success=True,
                errors=[]
            )

        except Exception as e:
            return ClearCartMutation(
                success=False,
                errors=[str(e)]
            )


class CartQuery(graphene.ObjectType):
    """
    Queries for cart app.
    """
    my_cart = graphene.Field(CartType)

    @login_required
    def resolve_my_cart(self, info):
        """Get current user's cart."""
        try:
            return info.context.user.cart
        except Cart.DoesNotExist:
            # Create empty cart if doesn't exist
            return Cart.objects.create(user=info.context.user)


class CartMutation(graphene.ObjectType):
    """
    Mutations for cart app.
    """
    add_to_cart = AddToCartMutation.Field()
    update_cart_item = UpdateCartItemMutation.Field()
    remove_from_cart = RemoveFromCartMutation.Field()
    clear_cart = ClearCartMutation.Field() 