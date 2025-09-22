# Backend E-commerce Diecast API

Backend API lengkap untuk e-commerce diecast dengan integrasi payment Midtrans, multiple image upload, dan sistem inventory management.

## 🚀 Features

- **Authentication & Authorization**: JWT-based dengan access/refresh tokens
- **Product Management**: CRUD produk dengan kategori, SKU, stok, harga  
- **Image Upload**: Multiple image upload dengan auto thumbnail generation
- **Storage**: MinIO integration untuk local S3-compatible storage
- **Shopping Cart**: Cart management dengan session persistence
- **Order Management**: Complete order flow dengan inventory tracking
- **Payment Integration**: Midtrans Snap integration dengan webhook handling
- **Admin Panel**: Admin-only endpoints untuk management
- **API Documentation**: Auto-generated OpenAPI (Swagger) docs

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Database**: PostgreSQL dengan SQLAlchemy 2.0 (async)
- **Storage**: MinIO (S3-compatible) untuk image storage
- **Image Processing**: Pillow untuk thumbnail generation
- **Authentication**: JWT dengan passlib bcrypt hashing
- **Payment**: Midtrans Snap API integration
- **Container**: Docker & docker-compose untuk development
- **Testing**: pytest dengan async support

## 📁 Project Structure

```
backend-ecommerce-python/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── core/
│   │   ├── config.py          # Application configuration
│   │   ├── security.py        # JWT & password utilities
│   │   └── events.py          # Startup/shutdown events
│   ├── db/
│   │   ├── base.py           # SQLAlchemy base classes
│   │   ├── session.py        # Database session management
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── crud.py           # CRUD operations
│   │   └── migrations/       # Alembic migrations
│   ├── api/
│   │   ├── deps.py           # FastAPI dependencies
│   │   └── v1/               # API v1 endpoints
│   │       ├── auth.py       # Authentication endpoints
│   │       ├── products.py   # Product management
│   │       ├── categories.py # Category management
│   │       ├── images.py     # Image upload endpoints
│   │       ├── carts.py      # Shopping cart
│   │       ├── orders.py     # Order management
│   │       ├── payments.py   # Payment creation
│   │       └── webhooks.py   # Payment webhooks
│   ├── schemas/              # Pydantic schemas
│   ├── services/
│   │   ├── storage.py        # MinIO storage service
│   │   ├── image.py          # Image processing service
│   │   └── midtrans.py       # Midtrans integration
│   └── tests/                # Unit tests
├── scripts/
│   ├── dev_start.sh          # Development startup script
│   └── init_db.sh            # Database initialization
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Development environment
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variables template
```

## 🚦 Quick Start

### 1. Setup Environment

```bash
# Clone repository
git clone <repository-url>
cd backend-ecommerce-python

# Copy environment template
cp .env.example .env

# Update .env with your configuration
nano .env
```

### 2. Start Development Environment

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Start all services (Docker required)
./scripts/dev_start.sh
```

Atau manual:

```bash
# Start containers
docker-compose up --build -d

# Run database migrations
docker-compose exec backend alembic upgrade head
```

### 3. Access Services

- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin123)
- **pgAdmin**: http://localhost:8080 (admin@admin.com/admin)

## 📝 Environment Configuration

Update `.env` dengan konfigurasi yang sesuai:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/diecastdb

# MinIO Storage
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123

# JWT Security
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-characters

# Midtrans (Get from https://dashboard.midtrans.com)
MIDTRANS_SERVER_KEY=your_midtrans_server_key
MIDTRANS_CLIENT_KEY=your_midtrans_client_key
MIDTRANS_IS_PRODUCTION=false

# CORS
FRONTEND_URL=http://localhost:3000
```

## 🔑 Authentication Flow

### Registration
```bash
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "securepassword",
  "full_name": "User Name"
}
```

### Login
```bash
POST /api/v1/auth/login
{
  "email": "user@example.com", 
  "password": "securepassword"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "User Name",
    "is_admin": false
  }
}
```

### Protected Requests
```bash
Authorization: Bearer <access_token>
```

## 🛒 API Usage Examples

### Create Product (Admin)
```bash
POST /api/v1/products
Authorization: Bearer <admin_token>
{
  "name": "Diecast Ferrari F40",
  "description": "Scale 1:18 Ferrari F40 Red",
  "price": 850000,
  "stock": 10,
  "brand": "Burago",
  "category_id": "uuid"
}
```

### Upload Images
```bash
POST /api/v1/products/{product_id}/images
Authorization: Bearer <admin_token>
Content-Type: multipart/form-data

files: [image1.jpg, image2.jpg, image3.jpg]
```

### Add to Cart
```bash
POST /api/v1/cart/items
Authorization: Bearer <user_token>
{
  "product_id": "uuid",
  "quantity": 2
}
```

### Create Order
```bash
POST /api/v1/orders
Authorization: Bearer <user_token>
{
  "items": [
    {
      "product_id": "uuid",
      "quantity": 2
    }
  ],
  "shipping_address": {
    "full_name": "John Doe",
    "phone": "081234567890",
    "address": "Jl. Example No. 123",
    "city": "Jakarta",
    "postal_code": "12345",
    "province": "DKI Jakarta"
  }
}
```

### Create Payment (Midtrans)
```bash
POST /api/v1/payments/create
Authorization: Bearer <user_token>
{
  "order_id": "uuid"
}
```

Response:
```json
{
  "snap_token": "abc123...",
  "redirect_url": "https://app.sandbox.midtrans.com/snap/v3/redirection/...",
  "order_id": "uuid"
}
```

## 💳 Payment Integration

### Midtrans Setup

1. **Daftar di Midtrans**: https://dashboard.midtrans.com
2. **Dapatkan Keys**:
   - Server Key (untuk backend)
   - Client Key (untuk frontend)
3. **Setup Webhook**: `https://yourdomain.com/api/v1/webhooks/midtrans`

### Payment Flow

1. User buat order → status `PENDING`
2. Call `/payments/create` → dapat `snap_token`
3. Frontend tampilkan Midtrans Snap UI
4. User bayar → Midtrans kirim notification ke webhook
5. Webhook update order status → `PAID`/`CANCELED`

## 🖼️ Image Upload & Processing

### Features
- **Multiple upload**: Up to 10 images per request
- **Auto thumbnails**: 300x300px thumbnails
- **Web optimization**: Max 1024px untuk display
- **Format support**: JPG, PNG, WebP
- **Storage**: MinIO dengan public URLs

### Upload Response
```json
{
  "images": [
    {
      "id": "uuid",
      "filename": "products/product-uuid/20240101_123456_abc123.jpg",
      "url": "http://localhost:9000/diecast/products/.../web_image.jpg",
      "thumbnail_url": "http://localhost:9000/diecast/.../thumb_image.jpg", 
      "is_primary": true,
      "width": 1920,
      "height": 1080,
      "size_bytes": 245760
    }
  ]
}
```

## 🧪 Testing

```bash
# Run all tests
docker-compose exec backend pytest

# Run specific test file
docker-compose exec backend pytest tests/test_auth.py

# Run with coverage
docker-compose exec backend pytest --cov=app tests/
```

## 🚀 Production Deployment

### 1. Environment Setup
```bash
# Production environment variables
PYTHON_ENV=production
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/db
MIDTRANS_IS_PRODUCTION=true
JWT_SECRET_KEY=super-secure-random-key
```

### 2. Database Migration
```bash
# Run migrations
alembic upgrade head
```

### 3. Docker Production
```dockerfile
# Production Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📊 Database Schema

### Core Tables
- `users` - User accounts & authentication
- `categories` - Product categories
- `products` - Product catalog dengan stock
- `product_images` - Multiple images per product
- `carts` & `cart_items` - Shopping cart
- `orders` & `order_items` - Order management
- `payments` - Payment transactions

### Key Relationships
- User → Orders (1:many)
- Product → Images (1:many) 
- Order → OrderItems → Products
- Order → Payments (1:many)

## 🔧 Troubleshooting

### Common Issues

**1. Database Connection Error**
```bash
# Check PostgreSQL container
docker-compose logs db
docker-compose restart db
```

**2. MinIO Connection Error**
```bash
# Check MinIO container
docker-compose logs minio
# Access MinIO console: http://localhost:9001
```

**3. Migration Errors**
```bash
# Reset migrations
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head
```

**4. Permission Issues**
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
chmod +x scripts/*.sh
```

## 📚 API Documentation

Lengkap tersedia di:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/auth/register` | User registration | - |
| POST | `/auth/login` | User login | - |
| GET | `/auth/me` | Current user info | User |
| GET | `/products` | List products | - |
| POST | `/products` | Create product | Admin |
| POST | `/products/{id}/images` | Upload images | Admin |
| GET | `/categories` | List categories | - |
| POST | `/cart/items` | Add to cart | User |
| POST | `/orders` | Create order | User |
| POST | `/payments/create` | Create payment | User |
| POST | `/webhooks/midtrans` | Payment webhook | - |

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Make changes
4. Add tests
5. Run linting: `ruff check app/`
6. Submit pull request

## 📄 License

MIT License - lihat file [LICENSE](LICENSE) untuk details.

---

## 🆘 Support

Untuk pertanyaan atau issues:
1. Check existing issues di GitHub
2. Buat issue baru dengan label yang sesuai
3. Sertakan log errors dan environment details

**Happy Coding! 🚗💨**