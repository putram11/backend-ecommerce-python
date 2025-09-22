from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from decimal import Decimal
from datetime import datetime
from uuid import UUID

# Base schemas
class BaseResponse(BaseModel):
    class Config:
        from_attributes = True


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase, BaseResponse):
    id: UUID
    is_active: bool
    is_admin: bool
    created_at: datetime


# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: User


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    user_id: Optional[str] = None


# Category schemas
class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase, BaseResponse):
    id: UUID
    created_at: datetime


# Product Image schemas
class ProductImageBase(BaseModel):
    filename: str
    is_primary: bool = False
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None


class ProductImageCreate(ProductImageBase):
    product_id: UUID


class ProductImage(ProductImageBase, BaseResponse):
    id: UUID
    url: Optional[str] = None
    created_at: datetime


# Product schemas
class ProductBase(BaseModel):
    sku: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: Decimal = Field(gt=0)
    stock: int = Field(ge=0)
    weight: Optional[Decimal] = None
    is_published: bool = False
    brand: Optional[str] = None


class ProductCreate(ProductBase):
    category_id: Optional[UUID] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    weight: Optional[Decimal] = None
    is_published: Optional[bool] = None
    brand: Optional[str] = None
    category_id: Optional[UUID] = None


class Product(ProductBase, BaseResponse):
    id: UUID
    category: Optional[Category] = None
    images: List[ProductImage] = []
    created_at: datetime
    updated_at: datetime


# Product List Response (for listing with pagination)
class ProductList(BaseResponse):
    id: UUID
    sku: str
    name: str
    price: Decimal
    stock: int
    is_published: bool
    brand: Optional[str] = None
    category: Optional[Category] = None
    primary_image: Optional[ProductImage] = None


class ProductListResponse(BaseModel):
    items: List[ProductList]
    total: int
    page: int
    per_page: int
    pages: int


# Cart schemas
class CartItemBase(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)


class CartItemCreate(CartItemBase):
    pass


class CartItem(BaseResponse):
    id: UUID
    quantity: int
    price_snapshot: Decimal
    product: Product
    created_at: datetime


class Cart(BaseResponse):
    id: UUID
    items: List[CartItem] = []
    created_at: datetime


# Order schemas  
class OrderItemBase(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)


class OrderItemCreate(OrderItemBase):
    pass


class OrderItem(BaseResponse):
    id: UUID
    sku_snapshot: str
    name_snapshot: str
    quantity: int
    price_snapshot: Decimal
    product: Optional[Product] = None


class ShippingAddress(BaseModel):
    full_name: str
    phone: str
    address: str
    city: str
    postal_code: str
    province: str


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    shipping_address: ShippingAddress
    notes: Optional[str] = None


class Order(BaseResponse):
    id: UUID
    order_number: str
    total_amount: Decimal
    status: str
    shipping_address: Optional[dict] = None
    notes: Optional[str] = None
    items: List[OrderItem] = []
    created_at: datetime
    updated_at: datetime


# Payment schemas
class PaymentCreate(BaseModel):
    order_id: UUID


class PaymentResponse(BaseModel):
    snap_token: str
    redirect_url: str
    order_id: UUID


class Payment(BaseResponse):
    id: UUID
    midtrans_transaction_id: str
    payment_type: Optional[str] = None
    transaction_status: str
    amount: Decimal
    created_at: datetime


# Pagination
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


# Product search/filter params
class ProductFilterParams(PaginationParams):
    search: Optional[str] = None
    category: Optional[UUID] = None
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    sort_by: str = Field(default="name")  # name, price, created_at
    sort_order: str = Field(default="asc")  # asc, desc


# Error response
class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None


# Multi-image upload response
class ImageUploadResponse(BaseModel):
    images: List[ProductImage]