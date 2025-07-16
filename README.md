# GraphQL E-commerce Backend

This is E-commerce backend built with **Django**, **GraphQL (Graphene)**, **JWT Authentication**, **Celery**, and **Redis**. Features include user management, product catalog, shopping cart, async checkout processing, and order management.

## Features

- JWT Authentication - Secure user registration, login, and token management
- Product Catalog - Products, categories, brands with filtering and pagination
- Shopping Cart - Add, update, remove items with real-time totals
- Async Checkout - Celery task chains for inventory validation, order creation, and stock updates
- Order Management - Order tracking, status updates, and cancellation
- Real-time Updates - Stock management and order status tracking
- Admin Interface - Django admin for product and order management

## Tech Stack

- **Backend**: Django 4.2.7, Python 3.12
- **GraphQL**: Graphene-Django
- **Authentication**: django-graphql-jwt
- **Database**: SQLite 
- **Task Queue**: Celery + Redis
- **Admin**: Django Admin Interface

## API Documentation

### 1. Authentication 

#### User Registration
```graphql
mutation {
  createUser(
    firstName: "Pawan"
    lastName: "Kumar" 
    email: "pawan@gmail.com"
    password: "securepassword123"
  ) {
    user {
      id
      firstName
      lastName
      email
    }
    success
    errors
  }
}
```

#### User Login
```graphql
mutation {
  tokenAuth(email: "pawan@gmail.com", password: "securepassword123") {
    token
    payload
    refreshExpiresIn
  }
}
```

#### Get Current User Profile
```graphql
# Requires: Authorization: Bearer <token>
query {
  me {
    id
    firstName
    lastName
    email
    fullName
    dateJoined
    addresses {
      id
      addressLine1
      city
      state
      country
    }
  }
}
```

#### Update Profile
```graphql
mutation {
  updateProfile(
    firstName: "Pawan"
    lastName: "Kumar"
  ) {
    user {
      id
      firstName
      lastName
      fullName
    }
    success
    errors
  }
}
```

#### Address Management
```graphql
# Create Address
mutation {
  createAddress(
    addressLine1: "123 MG Road"
    city: "Mumbai"
    state: "Maharashtra"
    postalCode: "400001"
    country: "India"
    isDefault: true
  ) {
    address {
      id
      addressLine1
      city
      state
      country
      isDefault
    }
    success
    errors
  }
}

# Get User Addresses
query {
  myAddresses {
    id
    addressLine1
    addressLine2
    city
    state
    postalCode
    country
    isDefault
  }
}
```

---

### 2. Products

#### Browse Products with Filtering
```graphql
query {
  products(
    first: 10
    categoryId: 1
    brandId: 1
    search: "MacBook"
    priceMin: "500"
    priceMax: "3000"
    inStock: true
  ) {
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
    edges {
      node {
        id
        name
        description
        price
        sku
        isInStock
        stockQuantity
        status
        brand {
          id
          name
        }
        category {
          id
          name
        }
        images {
          id
          image
          altText
          isMain
        }
        attributes {
          attribute {
            name
            attributeType
          }
          value
        }
      }
    }
  }
}
```

#### Get Single Product
```graphql
query {
  product(id: 1) {
    id
    name
    description
    price
    sku
    isInStock
    stockQuantity
    dimensionsLength
    dimensionsWidth
    dimensionsHeight
    weight
    brand {
      name
    }
    category {
      name
    }
    variants {
      id
      name
      sku
      price
      stockQuantity
      isInStock
      attributes {
        attribute {
          name
        }
        value
      }
    }
    images {
      image
      altText
      isMain
    }
  }
}
```

#### Get Categories
```graphql
query {
  categories {
    id
    name
    description
    isActive
    parent {
      id
      name
    }
    children {
      id
      name
    }
  }
}
```

#### Get Brands
```graphql
query {
  brands {
    id
    name
    description
    isActive
  }
}
```

---

### 3. Cart

#### Add to Cart
```graphql
mutation {
  addToCart(productId: 1, quantity: 2, variantId: 1) {
    success
    errors
    cartItem {
      id
      product {
        id
        name
        price
      }
      variant {
        id
        name
        price
      }
      quantity
      unitPrice
      totalPrice
      createdAt
    }
    cart {
      totalItems
      subtotal
    }
  }
}
```

#### View Cart
```graphql
query {
  myCart {
    id
    totalItems
    subtotal
    total
    createdAt
    updatedAt
    items {
      id
      product {
        id
        name
        price
        sku
        isInStock
      }
      variant {
        id
        name
        price
        sku
      }
      quantity
      unitPrice
      totalPrice
      createdAt
      updatedAt
    }
  }
}
```

#### Update Cart Item
```graphql
mutation {
  updateCartItem(
    productId: 1
    variantId: 1
    quantity: 5
  ) {
    success
    errors
    cartItem {
      id
      quantity
      unitPrice
      totalPrice
    }
    cart {
      totalItems
      subtotal
    }
  }
}
```

#### Remove from Cart
```graphql
# Set quantity to 0 to remove
mutation {
  updateCartItem(productId: 1, quantity: 0) {
    success
    errors
    cart {
      totalItems
      subtotal
    }
  }
}

# Or use removeFromCart
mutation {
  removeFromCart(productId: 1, variantId: 1) {
    success
    errors
    cart {
      totalItems
      subtotal
    }
  }
}
```

#### Clear Cart
```graphql
mutation {
  clearCart {
    success
    errors
    cart {
      totalItems
      subtotal
    }
  }
}
```

---

### 4. Checkout

#### Complete Checkout Process
```graphql
mutation {
  checkout(customer: {
    # Shipping Information (Required)
    shippingFirstName: "Pawan"
    shippingLastName: "Kumar"
    shippingCompany: "Tech Solutions"
    shippingAddressLine1: "123 MG Road"
    shippingAddressLine2: "Near Metro Station"
    shippingCity: "Mumbai"
    shippingState: "Maharashtra"
    shippingPostalCode: "400001"
    shippingCountry: "India"
    shippingPhone: "+91-9876543210"
    
    # Billing Information (Required)
    billingFirstName: "Pawan"
    billingLastName: "Kumar"
    billingCompany: "Tech Solutions"
    billingAddressLine1: "123 MG Road"
    billingAddressLine2: "Near Metro Station"
    billingCity: "Mumbai"
    billingState: "Maharashtra"
    billingPostalCode: "400001"
    billingCountry: "India"
    billingPhone: "+91-9876543210"
    
    # Optional
    notes: "Please deliver between 10 AM to 6 PM"
  }) {
    success
    errors
    order {
      id
      orderNumber
      status
      totalAmount
    }
  }
}
```

**Note**: Checkout uses async processing with Celery. The order is created in the background through these steps:
1. **Inventory Validation** - Checks stock availability
2. **Order Creation** - Creates order record
3. **Stock Deduction** - Updates inventory
4. **Confirmation** - Sends email and clears cart(Note: Print in console order details)

---

### 5. Orders

#### Get All User Orders
```graphql
query {
  myOrders {
    id
    orderNumber
    status
    paymentStatus
    subtotal
    taxAmount
    shippingAmount
    discountAmount
    totalAmount
    totalItems
    shippingAddress
    billingAddress
    notes
    trackingNumber
    shippedAt
    deliveredAt
    createdAt
    updatedAt
    canBeCancelled
    items {
      productName
      variantName
      productSku
      quantity
      unitPrice
      totalPrice
    }
  }
}
```

#### Get Specific Order
```graphql
query {
  order(id: "610cfd3b-0280-4205-9271-197a38282bd2") {
    id
    orderNumber
    status
    paymentStatus
    subtotal
    taxAmount
    shippingAmount
    discountAmount
    totalAmount
    totalItems
    shippingAddress
    billingAddress
    notes
    internalNotes
    trackingNumber
    shippedAt
    deliveredAt
    createdAt
    updatedAt
    canBeCancelled
    items {
      productName
      variantName
      productSku
      quantity
      unitPrice
      totalPrice
      createdAt
    }
  }
}
```

#### Cancel Order
```graphql
mutation {
  cancelOrder(orderId: "610cfd3b-0280-4205-9271-197a38282bd2") {
    success
    errors
    order {
      id
      orderNumber
      status
      canBeCancelled
    }
  }
}
```

---

## Order Status Flow

### Status Progression
- `pending` → `processing` → `confirmed` → `shipped` → `delivered`
- Can be `cancelled` (only if pending/processing/confirmed)
- Can be `refunded`

### GraphQL Mutations for Status Testing

**Check Order Status & History:**
```graphql
query GetOrder($id: ID!) {
  order(id: $id) {
    id
    orderNumber
    status
    paymentStatus
    canBeCancelled
    statusHistory {
      fromStatus
      toStatus
      notes
      createdAt
    }
    events {
      eventType
      message
      createdAt
    }
  }
}
```

**Cancel Order (Changes status to 'cancelled'):**
```graphql
mutation CancelOrder($orderId: ID!) {
  cancelOrder(orderId: $orderId) {
    order {
      id
      orderNumber
      status
      canBeCancelled
    }
    success
    errors
  }
}
```

## Payment Status Options

### Status Progression
- `pending` → `processing` → `paid`
- Can be `failed`, `refunded`, or `partially_refunded`

### Test Payment Flow with Checkout
```graphql
mutation Checkout($customer: CheckoutCustomerInput!) {
  checkout(customer: $customer) {
    order {
      id
      orderNumber
      status          # Will be 'pending'
      paymentStatus   # Will be 'pending'
      totalAmount
    }
    success
    errors
  }
}
```

----------------------------------------------------------------------------------------------------------------------------------------------

## Setup Instructions

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv ecommerce_env
source ecommerce_env/bin/activate  # Linux/Mac
# ecommerce_env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables
Create `.env` file:
```env
DEBUG=True
SECRET_KEY=django-insecure-local-development
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py create_sample_data  # Load sample products
python manage.py createsuperuser
```

### 4. Start Services
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
celery -A ecommerce worker --loglevel=info

# Terminal 3: Django Server
python manage.py runserver
```

### 5. Access Points
- **GraphQL Playground**: http://localhost:8000/graphql/
- **Django Admin**: http://localhost:8000/admin/
- **API Endpoint**: http://localhost:8000/graphql/

---

## Testing with Postman

### 1. Authentication Setup
1. **Login** with `tokenAuth` mutation
2. **Copy the token** from response
3. **Set Environment Variable**: `authToken = <your-token>`
4. **Add Header**: `Authorization: Bearer {{authToken}}`

### 2. Complete E-commerce Flow
1. **Register/Login** → Get auth token
2. **Browse Products** → Find products to buy
3. **Add to Cart** → Build your cart
4. **Checkout** → Create order (async processing)
5. **Check Orders** → View order status
6. **Continue Shopping** → Repeat cycle

---


### Docker Support
Use the included `Dockerfile` and `docker-compose.yml` for containerized deployment.

---

## Performance Features

- **Database Optimization**: Efficient queries with select_related/prefetch_related
- **Async Processing**: Celery for time-intensive operations
- **Caching**: Redis for session and task management
- **Stock Management**: Real-time inventory tracking
- **Audit Logging**: Complete operation history

---

## Security Features

- JWT token authentication
- CORS configuration
- SQL injection protection (Django ORM)
- XSS protection
- CSRF protection
- Input validation and sanitization

---

## Sample Data

The system includes sample data:
- **5 Products**: MacBook Pro, Dell XPS, iPhone, iPad, Monitor
- **2 Categories**: Electronics, Computers
- **2 Brands**: Apple, Dell
- **Product Attributes**: Color, Storage Capacity

Load with: `python manage.py create_sample_data`

---
