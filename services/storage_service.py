import os
import io
import mimetypes
from flask import current_app
from extensions import db
from models.document import Document
from config import is_serverless_environment
from services.file_validator import (
    validate_uploaded_file,
    generate_stored_filename,
    sanitize_original_filename,
    DOCUMENT_EXTENSIONS
)

class StorageService:
    """
    Unified Storage Service supporting:
    1. Local Filesystem (for local development)
    2. Cloud Object Storage (AWS S3, Cloudflare R2, MinIO, Supabase S3)
    3. PostgreSQL Database BLOB fallback (preserves files on Vercel when S3 is unconfigured)
    """

    @staticmethod
    def get_configured_backend() -> str:
        """
        Detect active storage backend:
        - If S3_BUCKET environment variable is present, use 's3'.
        - If running in serverless (Vercel) without S3, use 'database' to ensure persistence.
        - Otherwise use 'local' filesystem.
        """
        s3_bucket = os.environ.get('S3_BUCKET')
        if s3_bucket:
            return 's3'
        if is_serverless_environment():
            return 'database'
        return 'local'

    @staticmethod
    def _get_s3_client():
        """Lazily initialize boto3 S3 client."""
        try:
            import boto3
            endpoint_url = os.environ.get('S3_ENDPOINT_URL')
            region = os.environ.get('S3_REGION', 'us-east-1')
            
            kwargs = {'region_name': region}
            if endpoint_url:
                kwargs['endpoint_url'] = endpoint_url
            if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
                kwargs['aws_access_key_id'] = os.environ.get('AWS_ACCESS_KEY_ID')
                kwargs['aws_secret_access_key'] = os.environ.get('AWS_SECRET_ACCESS_KEY')

            return boto3.client('s3', **kwargs)
        except Exception as e:
            current_app.logger.error(f"Failed to initialize S3 client: {e}")
            return None

    @classmethod
    def save_document(cls, file_storage, title=None, category='General', description=None, user=None) -> Document:
        """
        Validate, store, and record metadata for uploaded documents (PDF, Word, etc.).
        """
        ext, file_size = validate_uploaded_file(file_storage, allowed_extensions=DOCUMENT_EXTENSIONS)
        
        orig_filename = sanitize_original_filename(file_storage.filename)
        stored_filename, ext = generate_stored_filename(orig_filename)
        
        if not title or not title.strip():
            # Use original filename without extension as default title
            title = orig_filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()

        backend = cls.get_configured_backend()
        mime_type = mimetypes.guess_type(orig_filename)[0] or 'application/octet-stream'

        file_storage.stream.seek(0)
        file_bytes = file_storage.read()

        doc = Document(
            title=title.strip(),
            original_filename=orig_filename,
            stored_filename=stored_filename,
            file_type=ext,
            mime_type=mime_type,
            file_size=file_size,
            file_category=category if category else 'General',
            description=description.strip() if description else None,
            storage_backend=backend,
            uploaded_by_id=user.id if user and user.is_authenticated else None
        )

        if backend == 's3':
            s3_client = cls._get_s3_client()
            bucket = os.environ.get('S3_BUCKET')
            if not s3_client or not bucket:
                raise RuntimeError("Cloud storage is configured for S3, but S3 client or S3_BUCKET is missing.")

            s3_key = f"documents/{stored_filename}"
            s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=file_bytes,
                ContentType=mime_type,
                Metadata={'original_filename': orig_filename}
            )
            doc.storage_key = s3_key

        elif backend == 'database':
            # Store in PostgreSQL binary column so serverless container restarts never lose files
            doc.file_blob = file_bytes
            doc.storage_key = f"db://documents/{stored_filename}"

        else:  # 'local'
            local_dir = current_app.config.get('DOCUMENTS_FOLDER')
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, stored_filename)
            with open(local_path, 'wb') as f:
                f.write(file_bytes)
            doc.storage_key = local_path

        db.session.add(doc)
        db.session.commit()
        return doc

    @classmethod
    def get_document_content(cls, doc: Document) -> tuple[io.BytesIO, str, str]:
        """
        Retrieve document binary content for downloading.
        Returns (BytesIO_stream, mime_type, download_filename).
        """
        mime = doc.mime_type or 'application/octet-stream'
        download_name = doc.original_filename

        if doc.storage_backend == 's3':
            s3_client = cls._get_s3_client()
            bucket = os.environ.get('S3_BUCKET')
            if not s3_client or not bucket:
                raise RuntimeError("Cloud storage is unavailable to retrieve file.")
            obj = s3_client.get_object(Bucket=bucket, Key=doc.storage_key)
            data = obj['Body'].read()
            return io.BytesIO(data), mime, download_name

        elif doc.storage_backend == 'database':
            if not doc.file_blob:
                raise FileNotFoundError("Document binary payload is missing from database.")
            return io.BytesIO(doc.file_blob), mime, download_name

        else:  # 'local'
            local_path = doc.storage_key
            if not local_path or not os.path.exists(local_path):
                # Check default documents directory
                fallback_path = os.path.join(current_app.config.get('DOCUMENTS_FOLDER', ''), doc.stored_filename)
                if os.path.exists(fallback_path):
                    local_path = fallback_path
                else:
                    raise FileNotFoundError(f"Local document file not found at {local_path}.")

            with open(local_path, 'rb') as f:
                data = f.read()
            return io.BytesIO(data), mime, download_name

    @classmethod
    def delete_document(cls, doc: Document) -> bool:
        """
        Delete document file content from storage backend and metadata from database.
        """
        try:
            if doc.storage_backend == 's3':
                s3_client = cls._get_s3_client()
                bucket = os.environ.get('S3_BUCKET')
                if s3_client and bucket and doc.storage_key:
                    try:
                        s3_client.delete_object(Bucket=bucket, Key=doc.storage_key)
                    except Exception as s3_err:
                        current_app.logger.warning(f"Failed to delete S3 object: {s3_err}")

            elif doc.storage_backend == 'local':
                local_path = doc.storage_key
                if local_path and os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except OSError as os_err:
                        current_app.logger.warning(f"Failed to delete local file: {os_err}")

            db.session.delete(doc)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting document {doc.id}: {e}")
            raise
