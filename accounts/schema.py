"""
GraphQL schema for accounts app.
"""
import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.decorators import login_required
import graphql_jwt

from .models import User, Address


class UserType(DjangoObjectType):
    """
    GraphQL type for User model.
    """
    full_name = graphene.String()
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 
            'phone', 'date_of_birth', 'is_verified', 'date_joined'
        )

    def resolve_full_name(self, info):
        return self.full_name


class UserAddressType(DjangoObjectType):
    """
    GraphQL type for Address model.
    """
    class Meta:
        model = Address
        fields = '__all__'


class CreateUserMutation(graphene.Mutation):
    """
    Mutation to create a new user account.
    """
    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        first_name = graphene.String(required=True)
        last_name = graphene.String(required=True)
        phone = graphene.String()

    user = graphene.Field(UserType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    def mutate(self, info, username, email, password, first_name, last_name, phone=None):
        try:
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                return CreateUserMutation(
                    success=False,
                    errors=['User with this email already exists']
                )
            
            if User.objects.filter(username=username).exists():
                return CreateUserMutation(
                    success=False,
                    errors=['User with this username already exists']
                )

            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone or ''
            )

            return CreateUserMutation(
                user=user,
                success=True,
                errors=[]
            )

        except Exception as e:
            return CreateUserMutation(
                success=False,
                errors=[str(e)]
            )


class UpdateProfileMutation(graphene.Mutation):
    """
    Mutation to update user profile.
    """
    class Arguments:
        first_name = graphene.String()
        last_name = graphene.String()
        phone = graphene.String()
        date_of_birth = graphene.Date()

    user = graphene.Field(UserType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @login_required
    def mutate(self, info, **kwargs):
        try:
            user = info.context.user
            
            for field, value in kwargs.items():
                if value is not None:
                    setattr(user, field, value)
            
            user.save()

            return UpdateProfileMutation(
                user=user,
                success=True,
                errors=[]
            )

        except Exception as e:
            return UpdateProfileMutation(
                success=False,
                errors=[str(e)]
            )


class CreateAddressMutation(graphene.Mutation):
    """
    Mutation to create a new address.
    """
    class Arguments:
        type = graphene.String(required=True)
        first_name = graphene.String(required=True)
        last_name = graphene.String(required=True)
        company = graphene.String()
        address_line_1 = graphene.String(required=True)
        address_line_2 = graphene.String()
        city = graphene.String(required=True)
        state = graphene.String(required=True)
        postal_code = graphene.String(required=True)
        country = graphene.String(required=True)
        phone = graphene.String()
        is_default = graphene.Boolean()

    address = graphene.Field(UserAddressType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    @login_required
    def mutate(self, info, **kwargs):
        try:
            user = info.context.user
            
            
            if kwargs.get('is_default', False):
                Address.objects.filter(
                    user=user, 
                    type=kwargs['type'], 
                    is_default=True
                ).update(is_default=False)

            address = Address.objects.create(user=user, **kwargs)

            return CreateAddressMutation(
                address=address,
                success=True,
                errors=[]
            )

        except Exception as e:
            return CreateAddressMutation(
                success=False,
                errors=[str(e)]
            )


class AccountsQuery(graphene.ObjectType):
    """
    Queries for accounts app.
    """
    me = graphene.Field(UserType)
    my_addresses = graphene.List(UserAddressType)

    @login_required
    def resolve_me(self, info):
        return info.context.user

    @login_required
    def resolve_my_addresses(self, info):
        return info.context.user.addresses.all()


class AccountsMutation(graphene.ObjectType):
    """
    Mutations for accounts app.
    """
    # JWT Authentication
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    
    # User management
    create_user = CreateUserMutation.Field()
    update_profile = UpdateProfileMutation.Field()
    create_address = CreateAddressMutation.Field() 