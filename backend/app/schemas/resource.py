from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class ResourceBase(BaseModel):
    resource_type: str  # link, pdf, text, media, unknown
    resource_url: Optional[str] = None
    resource_text: Optional[str] = None
    category: Optional[str] = "Other"

class ResourceCreate(ResourceBase):
    reel_id: UUID

class ResourceUpdate(BaseModel):
    category: Optional[str] = None
    notion_synced: Optional[bool] = None

class ResourceResponse(ResourceBase):
    id: UUID
    reel_id: UUID
    attachment_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    notion_page_id: Optional[str] = None
    notion_synced: bool
    received_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
