import io
import os
from typing import Tuple
from PIL import Image, ImageOps
from loguru import logger

from app.services.storage import storage_service


class ImageService:
    # Supported image formats
    SUPPORTED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP"}
    
    # Thumbnail sizes
    THUMBNAIL_SIZE = (300, 300)
    WEB_SIZE = (1024, 1024)
    
    def __init__(self):
        pass
    
    def validate_image(self, file_content: bytes) -> bool:
        """Validate if file is a supported image format"""
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                return img.format in self.SUPPORTED_FORMATS
        except Exception as e:
            logger.warning(f"Image validation failed: {e}")
            return False
    
    def get_image_info(self, file_content: bytes) -> Tuple[int, int, str]:
        """Get image dimensions and format"""
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                return img.width, img.height, img.format
        except Exception as e:
            logger.error(f"Failed to get image info: {e}")
            raise
    
    def create_thumbnail(
        self, 
        file_content: bytes, 
        size: Tuple[int, int] = None
    ) -> Tuple[bytes, int, int]:
        """Create thumbnail from image"""
        size = size or self.THUMBNAIL_SIZE
        
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create a white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create thumbnail using ImageOps.fit for better cropping
                thumbnail = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
                
                # Save to bytes
                output = io.BytesIO()
                thumbnail.save(output, format='JPEG', quality=85, optimize=True)
                thumbnail_bytes = output.getvalue()
                
                return thumbnail_bytes, thumbnail.width, thumbnail.height
                
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")
            raise
    
    def resize_for_web(
        self, 
        file_content: bytes, 
        max_size: Tuple[int, int] = None
    ) -> Tuple[bytes, int, int]:
        """Resize image for web display"""
        max_size = max_size or self.WEB_SIZE
        
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                # Only resize if image is larger than max_size
                if img.width <= max_size[0] and img.height <= max_size[1]:
                    # Image is already small enough
                    output = io.BytesIO()
                    if img.format == 'PNG':
                        img.save(output, format='PNG', optimize=True)
                    else:
                        if img.mode in ('RGBA', 'LA', 'P'):
                            img = img.convert('RGB')
                        img.save(output, format='JPEG', quality=90, optimize=True)
                    return output.getvalue(), img.width, img.height
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize maintaining aspect ratio
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save to bytes
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=90, optimize=True)
                resized_bytes = output.getvalue()
                
                return resized_bytes, img.width, img.height
                
        except Exception as e:
            logger.error(f"Failed to resize image for web: {e}")
            raise
    
    async def upload_product_images(
        self,
        product_id: str,
        original_filename: str,
        file_content: bytes
    ) -> dict:
        """Upload original image and create/upload thumbnail"""
        
        # Validate image
        if not self.validate_image(file_content):
            raise ValueError("Unsupported image format")
        
        # Get image info
        width, height, format_name = self.get_image_info(file_content)
        
        # Generate unique filename
        file_ext = original_filename.split('.')[-1].lower()
        if file_ext not in ['jpg', 'jpeg', 'png', 'webp']:
            file_ext = 'jpg'
        
        import uuid
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}.{file_ext}"
        
        # Storage paths
        original_key = f"products/{product_id}/{filename}"
        thumbnail_key = f"products/{product_id}/thumb_{filename}"
        web_key = f"products/{product_id}/web_{filename}"
        
        try:
            # Upload original image
            original_file = io.BytesIO(file_content)
            await storage_service.upload_fileobj(
                original_file,
                original_key,
                content_type=f"image/{file_ext}"
            )
            
            # Create and upload thumbnail
            thumbnail_content, thumb_width, thumb_height = self.create_thumbnail(file_content)
            thumbnail_file = io.BytesIO(thumbnail_content)
            await storage_service.upload_fileobj(
                thumbnail_file,
                thumbnail_key,
                content_type="image/jpeg"
            )
            
            # Create and upload web-optimized version
            web_content, web_width, web_height = self.resize_for_web(file_content)
            web_file = io.BytesIO(web_content)
            await storage_service.upload_fileobj(
                web_file,
                web_key,
                content_type="image/jpeg"
            )
            
            # Generate URLs
            original_url = storage_service.get_public_url(original_key)
            thumbnail_url = storage_service.get_public_url(thumbnail_key)
            web_url = storage_service.get_public_url(web_key)
            
            return {
                "filename": original_key,
                "original_url": original_url,
                "thumbnail_url": thumbnail_url,
                "web_url": web_url,
                "width": width,
                "height": height,
                "size_bytes": len(file_content),
                "thumbnail_width": thumb_width,
                "thumbnail_height": thumb_height,
                "web_width": web_width,
                "web_height": web_height
            }
            
        except Exception as e:
            # Clean up uploaded files on error
            logger.error(f"Failed to upload images for product {product_id}: {e}")
            
            # Try to clean up any uploaded files
            try:
                await storage_service.delete_object(original_key)
                await storage_service.delete_object(thumbnail_key)
                await storage_service.delete_object(web_key)
            except Exception:
                pass  # Ignore cleanup errors
            
            raise
    
    async def delete_product_images(self, product_id: str, filename: str) -> bool:
        """Delete all versions of a product image"""
        try:
            # Extract base filename without path
            base_filename = os.path.basename(filename)
            
            # Delete original, thumbnail, and web versions
            original_key = f"products/{product_id}/{base_filename}"
            thumbnail_key = f"products/{product_id}/thumb_{base_filename}"
            web_key = f"products/{product_id}/web_{base_filename}"
            
            await storage_service.delete_object(original_key)
            await storage_service.delete_object(thumbnail_key)
            await storage_service.delete_object(web_key)
            
            logger.info(f"Deleted all versions of image {base_filename} for product {product_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete images for product {product_id}, filename {filename}: {e}")
            return False


# Create global image service instance
image_service = ImageService()