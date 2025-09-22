from typing import Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.db.models import User, Product, Category, ProductImage, Cart, CartItem, Order, OrderItem, Payment
from app.core.security import get_password_hash, verify_password


class CRUDUser:
    async def get(self, db: AsyncSession, id: Any) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == id))
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(
        self, db: AsyncSession, *, email: str, password: str, full_name: str, is_admin: bool = False
    ) -> User:
        hashed_password = get_password_hash(password)
        db_obj = User(
            email=email,
            password_hash=hashed_password,
            full_name=full_name,
            is_admin=is_admin
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user


class CRUDCategory:
    async def get(self, db: AsyncSession, id: Any) -> Optional[Category]:
        result = await db.execute(select(Category).where(Category.id == id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Optional[Category]:
        result = await db.execute(select(Category).where(Category.slug == slug))
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Category]:
        result = await db.execute(
            select(Category).offset(skip).limit(limit).order_by(Category.name)
        )
        return result.scalars().all()

    async def create(
        self, db: AsyncSession, *, name: str, slug: str, description: str = None
    ) -> Category:
        db_obj = Category(name=name, slug=slug, description=description)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


class CRUDProduct:
    async def get(self, db: AsyncSession, id: Any) -> Optional[Product]:
        result = await db.execute(
            select(Product)
            .options(selectinload(Product.images), selectinload(Product.category))
            .where(Product.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_sku(self, db: AsyncSession, sku: str) -> Optional[Product]:
        result = await db.execute(
            select(Product)
            .options(selectinload(Product.images), selectinload(Product.category))
            .where(Product.sku == sku)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        category_id: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_published: bool = True
    ) -> List[Product]:
        query = select(Product).options(
            selectinload(Product.images), 
            selectinload(Product.category)
        )
        
        conditions = [Product.is_published == is_published] if is_published is not None else []
        
        if search:
            search_filter = or_(
                Product.name.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%")
            )
            conditions.append(search_filter)
        
        if category_id:
            conditions.append(Product.category_id == category_id)
            
        if min_price:
            conditions.append(Product.price >= min_price)
            
        if max_price:
            conditions.append(Product.price <= max_price)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.offset(skip).limit(limit).order_by(Product.name)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, **kwargs) -> Product:
        db_obj = Product(**kwargs)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: AsyncSession, *, db_obj: Product, **kwargs) -> Product:
        for field, value in kwargs.items():
            setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def decrease_stock(self, db: AsyncSession, *, product_id: str, quantity: int) -> bool:
        result = await db.execute(
            select(Product).where(Product.id == product_id).with_for_update()
        )
        product = result.scalar_one_or_none()
        
        if not product or product.stock < quantity:
            return False
        
        product.stock -= quantity
        await db.commit()
        return True


class CRUDProductImage:
    async def create(self, db: AsyncSession, **kwargs) -> ProductImage:
        db_obj = ProductImage(**kwargs)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_product(self, db: AsyncSession, product_id: str) -> List[ProductImage]:
        result = await db.execute(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.is_primary.desc(), ProductImage.created_at)
        )
        return result.scalars().all()


class CRUDCart:
    async def get_or_create_for_user(self, db: AsyncSession, user_id: str) -> Cart:
        result = await db.execute(
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .where(Cart.user_id == user_id)
        )
        cart = result.scalar_one_or_none()
        
        if not cart:
            cart = Cart(user_id=user_id)
            db.add(cart)
            await db.commit()
            await db.refresh(cart)
        
        return cart

    async def add_item(
        self, db: AsyncSession, *, cart_id: str, product_id: str, quantity: int, price: float
    ) -> CartItem:
        # Check if item already exists in cart
        result = await db.execute(
            select(CartItem).where(
                and_(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
            )
        )
        existing_item = result.scalar_one_or_none()
        
        if existing_item:
            existing_item.quantity += quantity
            existing_item.price_snapshot = price  # Update to latest price
            await db.commit()
            await db.refresh(existing_item)
            return existing_item
        else:
            item = CartItem(
                cart_id=cart_id,
                product_id=product_id,
                quantity=quantity,
                price_snapshot=price
            )
            db.add(item)
            await db.commit()
            await db.refresh(item)
            return item


class CRUDOrder:
    async def create(self, db: AsyncSession, **kwargs) -> Order:
        db_obj = Order(**kwargs)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get(self, db: AsyncSession, id: Any) -> Optional[Order]:
        result = await db.execute(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.payments)
            )
            .where(Order.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_order_number(self, db: AsyncSession, order_number: str) -> Optional[Order]:
        result = await db.execute(
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.payments)
            )
            .where(Order.order_number == order_number)
        )
        return result.scalar_one_or_none()


class CRUDPayment:
    async def create(self, db: AsyncSession, **kwargs) -> Payment:
        db_obj = Payment(**kwargs)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_midtrans_id(self, db: AsyncSession, midtrans_id: str) -> Optional[Payment]:
        result = await db.execute(
            select(Payment).where(Payment.midtrans_transaction_id == midtrans_id)
        )
        return result.scalar_one_or_none()


# Create instances
user = CRUDUser()
category = CRUDCategory()
product = CRUDProduct()
product_image = CRUDProductImage()
cart = CRUDCart()
order = CRUDOrder()
payment = CRUDPayment()