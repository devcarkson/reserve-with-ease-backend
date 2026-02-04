"""
Custom storage backend for R2
"""
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class R2Storage(S3Boto3Storage):
    """
    Custom R2 storage class that ensures proper configuration
    """
    
    def __init__(self, *args, **kwargs):
        # Override any settings that might be causing issues
        if not settings.USE_R2:
            raise RuntimeError("R2 storage is not enabled")
            
        # Ensure proper R2 configuration
        kwargs.setdefault('bucket_name', settings.R2_BUCKET_NAME)
        kwargs.setdefault('endpoint_url', settings.R2_ENDPOINT_URL)
        kwargs.setdefault('region_name', settings.R2_REGION)
        kwargs.setdefault('access_key', settings.R2_ACCESS_KEY_ID)
        kwargs.setdefault('secret_key', settings.R2_SECRET_ACCESS_KEY)
        kwargs.setdefault('default_acl', 'public-read')
        kwargs.setdefault('file_overwrite', False)
        kwargs.setdefault('querystring_auth', False)
        kwargs.setdefault('custom_domain', settings.R2_PUBLIC_URL)
        
        super().__init__(*args, **kwargs)
    
    def url(self, name):
        """
        Override URL generation to use public R2 URL instead of signed URLs
        """
        if self.custom_domain:
            # Use custom domain (public R2 URL) without query parameters
            return f"{self.custom_domain}/{name.lstrip('/')}"
        return super().url(name)
