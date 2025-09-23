from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from app.core.config import settings
from app.core.events import startup_event, shutdown_event
from app.api.v1 import auth, products, categories, images, carts, orders, payments, webhooks

# Configure logging
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# Create FastAPI app
app = FastAPI(
    title="Backend E-commerce Diecast API",
    description="""
    API Backend untuk e-commerce diecast dengan fitur:
    
    * **Authentication**: JWT-based user authentication dengan access & refresh tokens
    * **Product Management**: CRUD produk dengan kategori, SKU, stok, harga
    * **Image Upload**: Multiple image upload dengan thumbnail generation (MinIO storage)
    * **Cart & Orders**: Shopping cart dan order management dengan inventory tracking
    * **Payment Integration**: Midtrans Snap payment integration dengan webhook handling
    * **Admin Features**: Admin-only endpoints untuk product & category management
    
    ## Authentication
    
    Untuk mengakses protected endpoints, tambahkan header:
    ```
    Authorization: Bearer <your_access_token>
    ```
    
    ## Image Upload
    
    Upload multiple images dengan multipart/form-data:
    - Max 10 images per request
    - Max 10MB per image
    - Supported formats: JPG, PNG, WebP
    - Auto-generated thumbnails dan web-optimized versions
    
    ## Payment Flow
    
    1. User membuat order dari cart
    2. Panggil `/api/v1/payments/create` dengan order_id
    3. Dapatkan snap_token untuk frontend
    4. Frontend menampilkan Midtrans Snap UI
    5. Webhook `/api/v1/webhooks/midtrans` otomatis update status
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["Categories"]) 
app.include_router(images.router, prefix="/api/v1/products", tags=["Images"])  # images are under products
app.include_router(carts.router, prefix="/api/v1/cart", tags=["Shopping Cart"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])

# Event handlers
@app.on_event("startup")
async def on_startup():
    await startup_event(app)


@app.on_event("shutdown") 
async def on_shutdown():
    await shutdown_event(app)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Backend E-commerce Diecast API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "environment": settings.PYTHON_ENV
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.PYTHON_ENV,
        "database": "connected",  # Could add actual DB health check
        "storage": "connected"    # Could add actual MinIO health check
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.PYTHON_ENV == "development",
        log_level="info"
    )