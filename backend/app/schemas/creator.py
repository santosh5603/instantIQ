from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class CreatorBase(BaseModel):
    creator_name: str
    followed: bool = False
    purpose: Optional[str] = None

class CreatorCreate(CreatorBase):
    pass

class CreatorResponse(CreatorBase):
    id: UUID
    followed_at: Optional[datetime] = None
    unfollowed_at: Optional[datetime] = None
    blocked: bool
    last_interaction: Optional[datetime] = None
    total_reels: int
    total_resources: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
