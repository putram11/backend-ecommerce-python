"""
Database seeding script for initial data
"""
from app.db.session import get_session
from app.db import crud
from app.schemas import CategoryCreate, ProductCreate, UserCreate
from app.core.security import get_password_hash


async def seed_database():
    """Seed the database with initial data"""
    print("🌱 Starting database seeding...")
    
    async for db in get_session():
        try:
            # Create admin user
            admin_data = UserCreate(
                email="admin@diecast.com",
                password="admin123",
                full_name="Admin User",
                is_admin=True
            )
            
            admin_user = await crud.get_user_by_email(db, admin_data.email)
            if not admin_user:
                await crud.create_user(db, admin_data)
                print("✅ Admin user created (email: admin@diecast.com, password: admin123)")
            else:
                print("ℹ️  Admin user already exists")
            
            # Create categories
            categories = [
                {
                    "name": "Hot Wheels",
                    "description": "Koleksi Hot Wheels terlengkap dengan berbagai seri dan tahun"
                },
                {
                    "name": "Tomica", 
                    "description": "Diecast Tomica berkualitas tinggi dari Jepang"
                },
                {
                    "name": "Majorette",
                    "description": "Koleksi Majorette premium dengan detail sempurna"
                },
                {
                    "name": "Matchbox",
                    "description": "Diecast Matchbox klasik dan terbaru"
                },
                {
                    "name": "Greenlight",
                    "description": "Diecast Greenlight dengan lisensi resmi"
                }
            ]
            
            created_categories = {}
            for cat_data in categories:
                existing = await crud.get_category_by_name(db, cat_data["name"])
                if not existing:
                    category = CategoryCreate(**cat_data)
                    new_category = await crud.create_category(db, category)
                    created_categories[cat_data["name"]] = new_category.id
                    print(f"✅ Category '{cat_data['name']}' created")
                else:
                    created_categories[cat_data["name"]] = existing.id
                    print(f"ℹ️  Category '{cat_data['name']}' already exists")
            
            # Create sample products
            if created_categories:
                sample_products = [
                    {
                        "name": "Hot Wheels Lamborghini Huracan",
                        "description": "Diecast Hot Wheels Lamborghini Huracan skala 1:64 dengan detail interior dan eksterior yang sempurna",
                        "price": 25000,
                        "stock": 50,
                        "category_id": created_categories.get("Hot Wheels"),
                        "sku": "HW-LAMBO-001"
                    },
                    {
                        "name": "Tomica Toyota Supra",
                        "description": "Tomica Toyota Supra GR dengan opening doors dan detail engine bay",
                        "price": 45000,
                        "stock": 30,
                        "category_id": created_categories.get("Tomica"),
                        "sku": "TOM-SUPRA-001"
                    },
                    {
                        "name": "Majorette Ferrari F40",
                        "description": "Majorette Ferrari F40 dengan die-cast metal body dan rubber tires",
                        "price": 35000,
                        "stock": 25,
                        "category_id": created_categories.get("Majorette"),
                        "sku": "MAJ-F40-001"
                    },
                    {
                        "name": "Matchbox Land Rover Defender",
                        "description": "Matchbox Land Rover Defender dengan authentic livery dan realistic proportions",
                        "price": 20000,
                        "stock": 40,
                        "category_id": created_categories.get("Matchbox"),
                        "sku": "MB-DEFENDER-001"
                    },
                    {
                        "name": "Greenlight Ford Mustang GT500",
                        "description": "Greenlight Ford Mustang Shelby GT500 dengan opening hood dan detailed engine",
                        "price": 65000,
                        "stock": 15,
                        "category_id": created_categories.get("Greenlight"),
                        "sku": "GL-MUSTANG-001"
                    }
                ]
                
                for product_data in sample_products:
                    if product_data["category_id"]:  # Only create if category exists
                        existing_product = await crud.get_product_by_sku(db, product_data["sku"])
                        if not existing_product:
                            product = ProductCreate(**product_data)
                            await crud.create_product(db, product)
                            print(f"✅ Product '{product_data['name']}' created")
                        else:
                            print(f"ℹ️  Product '{product_data['name']}' already exists")
            
            print("🎉 Database seeding completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during seeding: {str(e)}")
            raise
        finally:
            break  # Exit the async generator