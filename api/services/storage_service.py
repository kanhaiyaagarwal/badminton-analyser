"""Storage abstraction layer for local and S3 storage."""

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, BinaryIO, Union
from datetime import datetime

from ..config import get_settings


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def save(self, file_path: str, data: Union[bytes, BinaryIO], content_type: str = None) -> str:
        """Save data to storage. Returns the storage key/path."""
        pass

    @abstractmethod
    def load(self, file_path: str) -> bytes:
        """Load data from storage."""
        pass

    @abstractmethod
    def get_url(self, file_path: str, expires: int = 3600) -> str:
        """Get URL to access the file. For local, returns file path. For S3, returns pre-signed URL."""
        pass

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """Delete file from storage. Returns True if successful."""
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    def copy(self, source: str, destination: str) -> str:
        """Copy file within storage. Returns destination path."""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _full_path(self, file_path: str) -> Path:
        """Get full filesystem path."""
        return self.base_dir / file_path

    def save(self, file_path: str, data: Union[bytes, BinaryIO], content_type: str = None) -> str:
        """Save data to local filesystem."""
        full_path = self._full_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(data, bytes):
            full_path.write_bytes(data)
        else:
            with open(full_path, 'wb') as f:
                shutil.copyfileobj(data, f)

        return file_path

    def load(self, file_path: str) -> bytes:
        """Load data from local filesystem."""
        full_path = self._full_path(file_path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return full_path.read_bytes()

    def get_url(self, file_path: str, expires: int = 3600) -> str:
        """Get local file path as URL."""
        return str(self._full_path(file_path))

    def delete(self, file_path: str) -> bool:
        """Delete file from local filesystem."""
        full_path = self._full_path(file_path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    def exists(self, file_path: str) -> bool:
        """Check if file exists locally."""
        return self._full_path(file_path).exists()

    def copy(self, source: str, destination: str) -> str:
        """Copy file locally."""
        src_path = self._full_path(source)
        dst_path = self._full_path(destination)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        return destination


class S3StorageBackend(StorageBackend):
    """AWS S3 storage backend."""

    def __init__(self, bucket: str, region: str, access_key: str = None, secret_key: str = None, cloudfront_domain: str = None):
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.region = region
        self.cloudfront_domain = cloudfront_domain

        # Use provided credentials or rely on IAM role / environment
        if access_key and secret_key:
            self.s3_client = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version='s3v4')
            )
        else:
            self.s3_client = boto3.client(
                's3',
                region_name=region,
                config=Config(signature_version='s3v4')
            )

    def save(self, file_path: str, data: Union[bytes, BinaryIO], content_type: str = None) -> str:
        """Upload data to S3."""
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

        if isinstance(data, bytes):
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=file_path,
                Body=data,
                **extra_args
            )
        else:
            self.s3_client.upload_fileobj(
                data,
                self.bucket,
                file_path,
                ExtraArgs=extra_args if extra_args else None
            )

        return file_path

    def load(self, file_path: str) -> bytes:
        """Download data from S3."""
        response = self.s3_client.get_object(Bucket=self.bucket, Key=file_path)
        return response['Body'].read()

    def get_url(self, file_path: str, expires: int = 3600) -> str:
        """Get pre-signed URL or CloudFront URL."""
        if self.cloudfront_domain:
            return f"https://{self.cloudfront_domain}/{file_path}"

        return self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': file_path},
            ExpiresIn=expires
        )

    def delete(self, file_path: str) -> bool:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=file_path)
            return True
        except Exception:
            return False

    def exists(self, file_path: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=file_path)
            return True
        except Exception:
            return False

    def copy(self, source: str, destination: str) -> str:
        """Copy file within S3."""
        self.s3_client.copy_object(
            Bucket=self.bucket,
            CopySource={'Bucket': self.bucket, 'Key': source},
            Key=destination
        )
        return destination

    def generate_upload_url(self, file_path: str, content_type: str, expires: int = 3600) -> dict:
        """Generate pre-signed URL for direct upload."""
        url = self.s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': self.bucket,
                'Key': file_path,
                'ContentType': content_type
            },
            ExpiresIn=expires
        )
        return {
            'upload_url': url,
            'file_key': file_path,
            'expires_in': expires
        }

    def initiate_multipart_upload(self, file_path: str, content_type: str) -> dict:
        """Initiate multipart upload for large files."""
        response = self.s3_client.create_multipart_upload(
            Bucket=self.bucket,
            Key=file_path,
            ContentType=content_type
        )
        return {
            'upload_id': response['UploadId'],
            'file_key': file_path
        }

    def generate_part_upload_url(self, file_path: str, upload_id: str, part_number: int, expires: int = 3600) -> str:
        """Generate pre-signed URL for uploading a part."""
        return self.s3_client.generate_presigned_url(
            'upload_part',
            Params={
                'Bucket': self.bucket,
                'Key': file_path,
                'UploadId': upload_id,
                'PartNumber': part_number
            },
            ExpiresIn=expires
        )

    def complete_multipart_upload(self, file_path: str, upload_id: str, parts: list) -> dict:
        """Complete multipart upload."""
        response = self.s3_client.complete_multipart_upload(
            Bucket=self.bucket,
            Key=file_path,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )
        return {
            'file_key': file_path,
            'location': response.get('Location')
        }

    def abort_multipart_upload(self, file_path: str, upload_id: str):
        """Abort multipart upload."""
        self.s3_client.abort_multipart_upload(
            Bucket=self.bucket,
            Key=file_path,
            UploadId=upload_id
        )


class StorageService:
    """Unified storage service that auto-switches between local and S3."""

    _instance: Optional['StorageService'] = None
    _upload_backend: Optional[StorageBackend] = None
    _output_backend: Optional[StorageBackend] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize storage backends based on config."""
        settings = get_settings()

        if settings.use_s3 and settings.s3_bucket:
            # Use S3 for both uploads and outputs
            self._upload_backend = S3StorageBackend(
                bucket=settings.s3_bucket,
                region=settings.aws_region,
                access_key=settings.aws_access_key_id or None,
                secret_key=settings.aws_secret_access_key or None,
                cloudfront_domain=settings.cloudfront_domain or None
            )
            self._output_backend = self._upload_backend
            self.storage_type = "s3"
        else:
            # Use local filesystem
            self._upload_backend = LocalStorageBackend(settings.upload_path)
            self._output_backend = LocalStorageBackend(settings.output_path)
            self.storage_type = "local"

    @property
    def uploads(self) -> StorageBackend:
        """Get uploads storage backend."""
        return self._upload_backend

    @property
    def outputs(self) -> StorageBackend:
        """Get outputs storage backend."""
        return self._output_backend

    def get_upload_path(self, user_id: int, filename: str) -> str:
        """Generate storage path for upload."""
        settings = get_settings()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = "".join(c for c in filename if c.isalnum() or c in '.-_')

        if self.storage_type == "s3":
            return f"{settings.s3_upload_prefix}/{user_id}/{timestamp}_{safe_filename}"
        else:
            return f"{user_id}/{timestamp}_{safe_filename}"

    def get_output_path(self, job_id: int, filename: str) -> str:
        """Generate storage path for analysis output."""
        settings = get_settings()

        if self.storage_type == "s3":
            return f"{settings.s3_output_prefix}/{job_id}/{filename}"
        else:
            return f"{job_id}/{filename}"

    def is_s3(self) -> bool:
        """Check if using S3 storage."""
        return self.storage_type == "s3"


def get_storage_service() -> StorageService:
    """Get storage service instance."""
    return StorageService()
