"""S3 service for handling S3-specific operations like pre-signed URLs and multipart uploads."""

from typing import Optional, List
from datetime import datetime

from ..config import get_settings
from .storage_service import get_storage_service, S3StorageBackend


class S3Service:
    """Service for S3-specific operations."""

    def __init__(self):
        self.settings = get_settings()
        self._storage = get_storage_service()

        if not self._storage.is_s3():
            self._s3_backend = None
        else:
            self._s3_backend: S3StorageBackend = self._storage.uploads

    def is_enabled(self) -> bool:
        """Check if S3 is enabled."""
        return self._s3_backend is not None

    def _require_s3(self):
        """Raise error if S3 is not enabled."""
        if not self.is_enabled():
            raise RuntimeError("S3 is not configured. Set USE_S3=true and S3_BUCKET in environment.")

    def generate_upload_url(
        self,
        user_id: int,
        filename: str,
        content_type: str,
        expires: int = 3600
    ) -> dict:
        """
        Generate pre-signed URL for direct client upload to S3.

        Returns:
            dict with upload_url, file_key, expires_in
        """
        self._require_s3()

        file_key = self._storage.get_upload_path(user_id, filename)

        return self._s3_backend.generate_upload_url(
            file_path=file_key,
            content_type=content_type,
            expires=expires
        )

    def generate_multipart_upload(
        self,
        user_id: int,
        filename: str,
        content_type: str,
        file_size: int,
        part_size: int = 10 * 1024 * 1024  # 10MB default part size
    ) -> dict:
        """
        Initiate multipart upload for large files (>100MB recommended).

        Returns:
            dict with upload_id, file_key, part_urls, part_count
        """
        self._require_s3()

        file_key = self._storage.get_upload_path(user_id, filename)

        # Initiate multipart upload
        result = self._s3_backend.initiate_multipart_upload(
            file_path=file_key,
            content_type=content_type
        )

        upload_id = result['upload_id']

        # Calculate parts
        part_count = (file_size + part_size - 1) // part_size
        part_urls = []

        for part_number in range(1, part_count + 1):
            url = self._s3_backend.generate_part_upload_url(
                file_path=file_key,
                upload_id=upload_id,
                part_number=part_number
            )
            part_urls.append({
                'part_number': part_number,
                'upload_url': url
            })

        return {
            'upload_id': upload_id,
            'file_key': file_key,
            'part_urls': part_urls,
            'part_count': part_count,
            'part_size': part_size
        }

    def complete_multipart_upload(
        self,
        file_key: str,
        upload_id: str,
        parts: List[dict]
    ) -> dict:
        """
        Complete multipart upload after all parts are uploaded.

        Args:
            file_key: The S3 key for the file
            upload_id: The upload ID from initiate
            parts: List of {PartNumber, ETag} for each uploaded part

        Returns:
            dict with file_key, location
        """
        self._require_s3()

        return self._s3_backend.complete_multipart_upload(
            file_path=file_key,
            upload_id=upload_id,
            parts=parts
        )

    def abort_multipart_upload(self, file_key: str, upload_id: str):
        """Abort/cancel a multipart upload."""
        self._require_s3()
        self._s3_backend.abort_multipart_upload(file_key, upload_id)

    def generate_download_url(self, file_key: str, expires: int = 3600) -> str:
        """Generate pre-signed download URL."""
        self._require_s3()
        return self._s3_backend.get_url(file_key, expires)

    def delete_file(self, file_key: str) -> bool:
        """Delete file from S3."""
        self._require_s3()
        return self._s3_backend.delete(file_key)

    def file_exists(self, file_key: str) -> bool:
        """Check if file exists in S3."""
        self._require_s3()
        return self._s3_backend.exists(file_key)

    def copy_file(self, source_key: str, dest_key: str) -> str:
        """Copy file within S3."""
        self._require_s3()
        return self._s3_backend.copy(source_key, dest_key)


# Singleton instance
_s3_service: Optional[S3Service] = None


def get_s3_service() -> S3Service:
    """Get S3 service singleton instance."""
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
    return _s3_service
