"""
Database seeding script for initial data
"""
import asyncio
from app.db.session import get_session
from app.db import crud


async def seed_database():
    """Seed the database with initial data"""
    print("🌱 Starting database seeding...")
    
    async for db in get_session():
        try:
            # Create admin user
            admin_email = "admin@diecast.com"
            
            admin_user = await crud.user.get_by_email(db, admin_email)
            if not admin_user:
                await crud.user.create(
                    db,
                    email=admin_email,
                    password="admin123",
                    full_name="Admin User",
                    is_admin=True
                )
                print("✅ Admin user created (email: admin@diecast.com, password: admin123)")
            else:
                print("ℹ️  Admin user already exists")
            
            # Create categories
            categories = [
                {
                    "name": "Hot Wheels",
                    "slug": "hot-wheels",
                    "description": "Koleksi Hot Wheels terlengkap dengan berbagai seri dan tahun"
                },
                {
                    "name": "Tomica",
                    "slug": "tomica", 
                    "description": "Diecast Tomica berkualitas tinggi dari Jepang"
                },
                {
                    "name": "Majorette",
                    "slug": "majorette",
                    "description": "Koleksi Majorette premium dengan detail sempurna"
                },
                {
                    "name": "Matchbox",
                    "slug": "matchbox",
                    "description": "Diecast Matchbox klasik dan terbaru"
                },
                {
                    "name": "Greenlight",
                    "slug": "greenlight",
                    "description": "Diecast Greenlight dengan lisensi resmi"
                }
            ]
            
            created_categories = {}
            for cat_data in categories:
                existing = await crud.category.get_by_slug(db, cat_data["slug"])
                if not existing:
                    new_category = await crud.category.create(db, **cat_data)
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
                        "sku": "HW-LAMBO-001",
                        "is_published": True
                    },
                    {
                        "name": "Tomica Toyota Supra",
                        "description": "Tomica Toyota Supra GR dengan opening doors dan detail engine bay",
                        "price": 45000,
                        "stock": 30,
                        "category_id": created_categories.get("Tomica"),
                        "sku": "TOM-SUPRA-001",
                        "is_published": True
                    },
                    {
                        "name": "Majorette Ferrari F40",
                        "description": "Majorette Ferrari F40 dengan die-cast metal body dan rubber tires",
                        "price": 35000,
                        "stock": 25,
                        "category_id": created_categories.get("Majorette"),
                        "sku": "MAJ-F40-001",
                        "is_published": True
                    },
                    {
                        "name": "Matchbox Land Rover Defender",
                        "description": "Matchbox Land Rover Defender dengan authentic livery dan realistic proportions",
                        "price": 20000,
                        "stock": 40,
                        "category_id": created_categories.get("Matchbox"),
                        "sku": "MB-DEFENDER-001",
                        "is_published": True
                    },
                    {
                        "name": "Greenlight Ford Mustang GT500",
                        "description": "Greenlight Ford Mustang Shelby GT500 dengan opening hood dan detailed engine",
                        "price": 65000,
                        "stock": 15,
                        "category_id": created_categories.get("Greenlight"),
                        "sku": "GL-MUSTANG-001",
                        "is_published": True
                    }
                ]
                
                for product_data in sample_products:
                    if product_data["category_id"]:  # Only create if category exists
                        existing_product = await crud.product.get_by_sku(db, product_data["sku"])
                        if not existing_product:
                            await crud.product.create(db, **product_data)
                            print(f"✅ Product '{product_data['name']}' created")
                        else:
                            print(f"ℹ️  Product '{product_data['name']}' already exists")
            
            print("🎉 Database seeding completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during seeding: {str(e)}")
            raise
        finally:
            break  # Exit the async generator


if __name__ == "__main__":
    asyncio.run(seed_database())