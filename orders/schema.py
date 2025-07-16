"""
GraphQL schema for orders app.
"""
import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required

from .models import Order, OrderItem, OrderStatusHistory, OrderEvent
from .tasks import process_checkout


class OrderItemType(DjangoObjectType):
    """
    GraphQL type for OrderItem model.
    """
    class Meta:
        model = OrderItem
        fields = '__all__'


class OrderStatusHistoryType(DjangoObjectType):
    """
    GraphQL type for OrderStatusHistory model.
    """
    class Meta:
        model = OrderStatusHistory
        fields = '__all__'


class OrderEventType(DjangoObjectType):
    """
    GraphQL type for OrderEvent model.
    """
    class Meta:
        model = OrderEvent
        fields = '__all__'


class OrderType(DjangoObjectType):
    """
    GraphQL type for Order model.
    """
    total_items = graphene.Int()
    shipping_address = graphene.String()
    billing_address = graphene.String()
    can_be_cancelled = graphene.Boolean()
    
    class Meta:
        model = Order
        fields = '__all__'
        
    def resolve_total_items(self, info):
        return self.total_items
        
    def resolve_shipping_address(self, info):
        return self.shipping_address
        
    def resolve_billing_address(self, info):
        return self.billing_address
        
    def resolve_can_be_cancelled(self, info):
        return self.can_be_cancelled()


class CheckoutInput(graphene.InputObjectType):
    """
    Input type for checkout information.
    """
    # Shipping information
    shipping_first_name = graphene.String(required=True)
    shipping_last_name = graphene.String(required=True)
    shipping_company = graphene.String()
    shipping_address_line_1 = graphene.String(required=True)
    shipping_address_line_2 = graphene.String()
    shipping_city = graphene.String(required=True)
    shipping_state = graphene.String(required=True)
    shipping_postal_code = graphene.String(required=True)
    shipping_country = graphene.String(required=True)
    shipping_phone = graphene.String()
    
    # Billing information
    billing_first_name = graphene.String(required=True)
    billing_last_name = graphene.String(required=True)
    billing_company = graphene.String()
    billing_address_line_1 = graphene.String(required=True)
    billing_address_line_2 = graphene.String()
    billing_city = graphene.String(required=True)
    billing_state = graphene.String(required=True)
    billing_postal_code = graphene.String(required=True)
    billing_country = graphene.String(required=True)
    billing_phone = graphene.String()
    
    # Additional information
    notes = graphene.String()


class CheckoutMutation(graphene.Mutation):
    """
    Mutation to checkout and create an order from cart.
    """
    class Arguments:
        customer = CheckoutInput(required=True)

    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @login_required
    def mutate(self, info, customer):
        try:
            user = info.context.user
            
            # Get user's cart
            try:
                cart = user.cart
            except:
                return CheckoutMutation(
                    success=False,
                    errors=['Cart not found']
                )
            
            # Check if cart has items
            if not cart.items.exists():
                return CheckoutMutation(
                    success=False,
                    errors=['Cart is empty']
                )
            
            # Validate all cart items are still available
            for item in cart.items.all():
                try:
                    item.clean()  # This will validate stock and product status
                except Exception as e:
                    return CheckoutMutation(
                        success=False,
                        errors=[str(e)]
                    )
            
            # Create order data (user will be added in the task)
            order_data = {
                'subtotal': cart.subtotal,
                'tax_amount': 0,  # Can be calculated based on location
                'shipping_amount': 0,  # Can be calculated based on shipping method
                'discount_amount': 0,  # Can be applied if there are coupons
                'total_amount': cart.subtotal,
                **customer
            }
            
            # Start async checkout process
            task = process_checkout.delay(
                user_id=user.id,
                cart_id=str(cart.id),
                order_data=order_data
            )
            
            # Note: In a real implementation, you might want to return a checkout session ID
            # and allow the client to poll for the order status
            
            return CheckoutMutation(
                success=True,
                errors=[],
                order=None  # Order will be created asynchronously
            )

        except Exception as e:
            return CheckoutMutation(
                success=False,
                errors=[str(e)]
            )


class CancelOrderMutation(graphene.Mutation):
    """
    Mutation to cancel an order.
    """
    class Arguments:
        order_id = graphene.ID(required=True)

    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @login_required
    def mutate(self, info, order_id):
        try:
            user = info.context.user
            
            # Get order
            try:
                order = user.orders.get(id=order_id)
            except Order.DoesNotExist:
                return CancelOrderMutation(
                    success=False,
                    errors=['Order not found']
                )
            
            # Check if order can be cancelled
            if not order.can_be_cancelled():
                return CancelOrderMutation(
                    success=False,
                    errors=['Order cannot be cancelled at this stage']
                )
            
            # Cancel order
            order.cancel()

            return CancelOrderMutation(
                order=order,
                success=True,
                errors=[]
            )

        except Exception as e:
            return CancelOrderMutation(
                success=False,
                errors=[str(e)]
            )


class OrdersQuery(graphene.ObjectType):
    """
    Queries for orders app.
    """
    my_orders = graphene.List(OrderType)
    order = graphene.Field(OrderType, id=graphene.ID(required=True))

    @login_required
    def resolve_my_orders(self, info):
        """Get current user's orders."""
        return info.context.user.orders.all().order_by('-created_at')

    @login_required
    def resolve_order(self, info, id):
        """Get specific order by ID."""
        try:
            return info.context.user.orders.get(id=id)
        except Order.DoesNotExist:
            return None


class OrdersMutation(graphene.ObjectType):
    """
    Mutations for orders app.
    """
    checkout = CheckoutMutation.Field()
    cancel_order = CancelOrderMutation.Field() 