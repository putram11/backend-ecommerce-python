from sqlalchemy import Column, String, Boolean, Integer, Text, Numeric, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.db.base import Base, UUIDMixin, TimestampMixin


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    SHIPPING = "SHIPPING"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"
    REFUNDED = "REFUNDED"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SETTLEMENT = "settlement"
    CAPTURE = "capture"
    DENY = "deny"
    CANCEL = "cancel"
    EXPIRE = "expire"
    FAILURE = "failure"
    REFUND = "refund"
    PARTIAL_REFUND = "partial_refund"
    AUTHORIZE = "authorize"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    carts = relationship("Cart", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")


class Category(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "categories"
    
    name = Column(String(255), unique=True, nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    
    # Relationships
    products = relationship("Product", back_populates="category")


class Product(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "products"
    
    sku = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, default=0, nullable=False)
    weight = Column(Numeric(8, 2))  # in grams for shipping calculation
    is_published = Column(Boolean, default=False, nullable=False)
    brand = Column(String(100))
    
    # Foreign Keys
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    
    # Relationships
    category = relationship("Category", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")


class ProductImage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "product_images"
    
    filename = Column(String(255), nullable=False)  # MinIO key
    url = Column(String(500))  # cached public/presigned URL
    is_primary = Column(Boolean, default=False, nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    size_bytes = Column(Integer)
    
    # Foreign Keys
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="images")


class Cart(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "carts"
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="carts")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "cart_items"
    
    quantity = Column(Integer, nullable=False, default=1)
    price_snapshot = Column(Numeric(10, 2), nullable=False)  # price at time of adding to cart
    
    # Foreign Keys
    cart_id = Column(UUID(as_uuid=True), ForeignKey("carts.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    # Relationships
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product", back_populates="cart_items")


class Order(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "orders"
    
    order_number = Column(String(100), unique=True, nullable=False, index=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), nullable=False, default=OrderStatus.PENDING)
    shipping_address = Column(JSON)  # Store address as JSON
    notes = Column(Text)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "order_items"
    
    sku_snapshot = Column(String(100), nullable=False)  # SKU at time of order
    name_snapshot = Column(String(255), nullable=False)  # Product name at time of order
    quantity = Column(Integer, nullable=False)
    price_snapshot = Column(Numeric(10, 2), nullable=False)  # Price at time of order
    
    # Foreign Keys
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"
    
    midtrans_transaction_id = Column(String(255), unique=True, nullable=False, index=True)
    payment_type = Column(String(50))
    transaction_status = Column(String(50), nullable=False)
    raw_payload = Column(JSON)  # Store complete webhook payload
    amount = Column(Numeric(10, 2), nullable=False)
    
    # Foreign Keys
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="payments")