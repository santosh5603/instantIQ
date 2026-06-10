from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum

class ReelStatus(str, Enum):
    PENDING             = "pending"
    EXTRACTING_CAPTION  = "extracting_caption"
    CTA_DETECTED        = "cta_detected"
    NO_CTA              = "no_cta"
    AWAITING_FOLLOW     = "awaiting_follow"
    FOLLOWING           = "following"
    AWAITING_COMMENT    = "awaiting_comment"
    COMMENTING          = "commenting"
    COMMENTED           = "commented"
    WAITING_DM          = "waiting_dm"
    DM_RECEIVED         = "dm_received"
    EXTRACTING_RESOURCE = "extracting_resource"
    COMPLETED           = "completed"
    FAILED              = "failed"
    DM_TIMEOUT          = "dm_timeout"
    RETRYING            = "retrying"

class ReelBase(BaseModel):
    reel_url: str
    creator_name: Optional[str] = None

class ReelCreate(ReelBase):
    pass

class ReelResponse(BaseModel):
    id: UUID
    reel_url: str
    creator_name: Optional[str] = None
    caption: Optional[str] = None
    requires_comment: bool
    requires_follow: bool
    requires_dm: bool
    comment_keyword: Optional[str] = None
    dm_keyword: Optional[str] = None
    cta_confidence: Optional[float] = None
    commented: bool
    comment_posted_at: Optional[datetime] = None
    followed: bool
    followed_at: Optional[datetime] = None
    status: ReelStatus
    error_message: Optional[str] = None
    retry_count: int
    notion_synced: bool
    notion_page_id: Optional[str] = None
    dm_message_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
