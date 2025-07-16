"""
Main GraphQL schema combining all app schemas.
"""
import graphene
from graphql_jwt.decorators import login_required

# Import schemas from apps
from accounts.schema import AccountsQuery, AccountsMutation
from products.schema import ProductsQuery
from cart.schema import CartQuery, CartMutation
from orders.schema import OrdersQuery, OrdersMutation
from orders.subscriptions import Subscriptions


class Query(
    AccountsQuery,
    ProductsQuery,
    CartQuery,
    OrdersQuery,
    graphene.ObjectType
):
    """
    Root Query combining all app queries.
    """
    pass


class Mutation(
    AccountsMutation,
    CartMutation,
    OrdersMutation,
    graphene.ObjectType
):
    """
    Root Mutation combining all app mutations.
    """
    pass


# Main schema with all imports restored
schema = graphene.Schema(query=Query, mutation=Mutation, subscription=Subscriptions) 