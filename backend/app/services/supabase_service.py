import os
from typing import Tuple, Optional
from supabase import create_client, Client
from app.config import settings
import logging

logger = logging.getLogger("supabase_service")

class SupabaseService:
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_SERVICE_KEY
        self.bucket_name = settings.SUPABASE_STORAGE_BUCKET
        
        # Initialize client if configurations are valid and not dummy values
        if self.url and self.key and "dummy" not in self.url and "dummy" not in self.key:
            try:
                self.client: Optional[Client] = create_client(self.url, self.key)
                logger.info("Supabase Client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase Client: {str(e)}")
                self.client = None
        else:
            logger.warning("Supabase URL or Key is dummy/empty. Supabase operations will run in mock mode.")
            self.client = None

    def upload_file(self, local_file_path: str, destination_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Uploads a file to Supabase Storage.
        
        Args:
            local_file_path: Path to the local file to upload.
            destination_path: Remote path in the bucket (e.g., "reels/reel_id/file.pdf")
            
        Returns:
            Tuple[bool, public_url, error_message]
        """
        if not self.client:
            logger.warning(f"[Mock] Uploading {local_file_path} to {destination_path} in bucket {self.bucket_name}")
            mock_url = f"https://mock.supabase.storage/v1/object/public/{self.bucket_name}/{destination_path}"
            return True, mock_url, None

        if not os.path.exists(local_file_path):
            return False, None, f"Local file does not exist: {local_file_path}"

        try:
            # Clean remote destination path
            destination_path = destination_path.lstrip("/")
            
            with open(local_file_path, 'rb') as f:
                file_data = f.read()

            # Perform the upload
            # Note: We use upsert=True to overwrite if file exists (useful for retries)
            response = self.client.storage.from_(self.bucket_name).upload(
                path=destination_path,
                file=file_data,
                file_options={"x-upsert": "true"}
            )
            
            # Fetch public URL
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(destination_path)
            logger.info(f"Uploaded file successfully to Supabase Storage: {public_url}")
            return True, public_url, None
            
        except Exception as e:
            logger.error(f"Error uploading file to Supabase Storage: {str(e)}")
            return False, None, str(e)

supabase_service = SupabaseService()
