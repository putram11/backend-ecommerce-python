from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.api.deps import get_db, get_current_admin_user
from app.db import crud
from app.schemas import ProductImage, ImageUploadResponse
from app.services.image import image_service

router = APIRouter()


async def process_image_upload(
    db: AsyncSession,
    product_id: UUID,
    file: UploadFile,
    is_primary: bool = False
) -> ProductImage:
    """Background task to process image upload"""
    
    # Read file content
    file_content = await file.read()
    
    # Upload and process image
    image_data = await image_service.upload_product_images(
        str(product_id),
        file.filename or "image.jpg",
        file_content
    )
    
    # Create database record
    product_image = await crud.product_image.create(
        db,
        product_id=product_id,
        filename=image_data["filename"],
        url=image_data["web_url"],
        is_primary=is_primary,
        width=image_data["width"],
        height=image_data["height"],
        size_bytes=image_data["size_bytes"]
    )
    
    return product_image


@router.post("/{product_id}/images", response_model=ImageUploadResponse)
async def upload_product_images(
    product_id: UUID,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """Upload multiple images for a product (admin only)"""
    
    # Verify product exists
    product = await crud.product.get(db, id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Validate files
    if not files or len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    if len(files) > 10:  # Limit number of files
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many files. Maximum 10 files allowed"
        )
    
    # Check if product already has images
    existing_images = await crud.product_image.get_by_product(db, str(product_id))
    has_primary = any(img.is_primary for img in existing_images)
    
    uploaded_images = []
    
    for i, file in enumerate(files):
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' is not a valid image"
            )
        
        # Validate file size (max 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' is too large. Maximum size is 10MB"
            )
        
        # Reset file position
        await file.seek(0)
        
        # Set first image as primary if no primary image exists
        is_primary = i == 0 and not has_primary
        
        try:
            # Process upload
            product_image = await process_image_upload(
                db, product_id, file, is_primary
            )
            uploaded_images.append(product_image)
            
        except Exception as e:
            # If any upload fails, we should clean up previously uploaded images
            # For now, we'll just log the error and continue
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload image '{file.filename}': {str(e)}"
            )
    
    return ImageUploadResponse(images=uploaded_images)


@router.delete("/{product_id}/images/{image_id}")
async def delete_product_image(
    product_id: UUID,
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """Delete a product image (admin only)"""
    
    # Verify product exists
    product = await crud.product.get(db, id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Find image
    product_images = await crud.product_image.get_by_product(db, str(product_id))
    image = next((img for img in product_images if img.id == image_id), None)
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Delete from storage
    await image_service.delete_product_images(str(product_id), image.filename)
    
    # Delete from database
    await db.delete(image)
    await db.commit()
    
    return {"detail": "Image deleted successfully"}


@router.put("/{product_id}/images/{image_id}/primary")
async def set_primary_image(
    product_id: UUID,
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """Set an image as primary for the product (admin only)"""
    
    # Verify product exists
    product = await crud.product.get(db, id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Get all product images
    product_images = await crud.product_image.get_by_product(db, str(product_id))
    
    # Find the target image
    target_image = next((img for img in product_images if img.id == image_id), None)
    if not target_image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Update all images - set target as primary, others as non-primary
    for image in product_images:
        image.is_primary = (image.id == image_id)
    
    await db.commit()
    
    return {"detail": "Primary image updated successfully"}


@router.get("/{image_id}/url")
async def get_image_url(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    expires_in: int = 3600
):
    """Get presigned URL for image access"""
    
    # This is a simplified version - in production you might want to
    # store image records in a separate table for faster lookup
    from app.services.storage import storage_service
    
    # Find image in database (you might want to optimize this query)
    result = await db.execute(
        """
        SELECT filename FROM product_images WHERE id = :image_id
        """,
        {"image_id": str(image_id)}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Generate presigned URL
    try:
        url = await storage_service.generate_presigned_url(
            row[0],
            expiration=expires_in
        )
        return {"url": url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate URL: {str(e)}"
        )