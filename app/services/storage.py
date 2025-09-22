from typing import Optional, List, IO
import aioboto3
from botocore.exceptions import ClientError
from loguru import logger

from app.core.config import settings


class StorageService:
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = f"{'https' if settings.S3_USE_SSL else 'http'}://{settings.MINIO_ENDPOINT}"
        
    async def _get_client(self):
        """Get S3 client"""
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            use_ssl=settings.S3_USE_SSL
        )
    
    async def create_bucket_if_not_exists(self, bucket_name: str) -> bool:
        """Create bucket if it doesn't exist"""
        try:
            async with await self._get_client() as client:
                # Check if bucket exists
                try:
                    await client.head_bucket(Bucket=bucket_name)
                    logger.info(f"Bucket '{bucket_name}' already exists")
                    return True
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        # Bucket doesn't exist, create it
                        await client.create_bucket(Bucket=bucket_name)
                        logger.info(f"Created bucket '{bucket_name}'")
                        return True
                    else:
                        raise e
        except Exception as e:
            logger.error(f"Failed to create bucket '{bucket_name}': {e}")
            raise
    
    async def upload_fileobj(
        self, 
        file_obj: IO, 
        key: str, 
        bucket: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> str:
        """Upload file object to storage"""
        bucket = bucket or settings.MINIO_BUCKET
        
        try:
            async with await self._get_client() as client:
                extra_args = {}
                if content_type:
                    extra_args["ContentType"] = content_type
                
                await client.upload_fileobj(
                    file_obj, 
                    bucket, 
                    key,
                    ExtraArgs=extra_args
                )
                
                logger.info(f"Uploaded file to {bucket}/{key}")
                return key
        except Exception as e:
            logger.error(f"Failed to upload file to {bucket}/{key}: {e}")
            raise
    
    async def upload_file(
        self,
        file_path: str,
        key: str,
        bucket: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> str:
        """Upload file from path to storage"""
        bucket = bucket or settings.MINIO_BUCKET
        
        try:
            async with await self._get_client() as client:
                extra_args = {}
                if content_type:
                    extra_args["ContentType"] = content_type
                
                await client.upload_file(
                    file_path,
                    bucket,
                    key,
                    ExtraArgs=extra_args
                )
                
                logger.info(f"Uploaded file {file_path} to {bucket}/{key}")
                return key
        except Exception as e:
            logger.error(f"Failed to upload file {file_path} to {bucket}/{key}: {e}")
            raise
    
    async def generate_presigned_url(
        self,
        key: str,
        bucket: Optional[str] = None,
        expiration: int = 3600,
        method: str = "get_object"
    ) -> str:
        """Generate presigned URL for object access"""
        bucket = bucket or settings.MINIO_BUCKET
        
        try:
            async with await self._get_client() as client:
                url = await client.generate_presigned_url(
                    method,
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=expiration
                )
                return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {bucket}/{key}: {e}")
            raise
    
    async def delete_object(self, key: str, bucket: Optional[str] = None) -> bool:
        """Delete object from storage"""
        bucket = bucket or settings.MINIO_BUCKET
        
        try:
            async with await self._get_client() as client:
                await client.delete_object(Bucket=bucket, Key=key)
                logger.info(f"Deleted object {bucket}/{key}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete object {bucket}/{key}: {e}")
            return False
    
    async def list_objects(
        self,
        prefix: Optional[str] = None,
        bucket: Optional[str] = None,
        max_keys: int = 1000
    ) -> List[dict]:
        """List objects in bucket with optional prefix"""
        bucket = bucket or settings.MINIO_BUCKET
        
        try:
            async with await self._get_client() as client:
                kwargs = {"Bucket": bucket, "MaxKeys": max_keys}
                if prefix:
                    kwargs["Prefix"] = prefix
                
                response = await client.list_objects_v2(**kwargs)
                return response.get("Contents", [])
        except Exception as e:
            logger.error(f"Failed to list objects in {bucket} with prefix {prefix}: {e}")
            raise
    
    async def object_exists(self, key: str, bucket: Optional[str] = None) -> bool:
        """Check if object exists in storage"""
        bucket = bucket or settings.MINIO_BUCKET
        
        try:
            async with await self._get_client() as client:
                await client.head_object(Bucket=bucket, Key=key)
                return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise e
    
    def get_public_url(self, key: str, bucket: Optional[str] = None) -> str:
        """Get public URL for object (if bucket is public)"""
        bucket = bucket or settings.MINIO_BUCKET
        return f"{self.endpoint_url}/{bucket}/{key}"


# Create global storage service instance
storage_service = StorageService()