from sqlalchemy import Column, String, Boolean, Float, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base
import uuid

class Reel(Base):
    __tablename__ = "reels"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reel_url          = Column(Text, nullable=False, unique=True)
    creator_name      = Column(String(255))
    caption           = Column(Text)
    requires_comment  = Column(Boolean, default=False)
    requires_follow   = Column(Boolean, default=False)
    requires_dm       = Column(Boolean, default=False)
    comment_keyword   = Column(String(100))
    dm_keyword        = Column(String(100))
    cta_confidence    = Column(Float)
    commented         = Column(Boolean, default=False)
    comment_posted_at = Column(TIMESTAMP(timezone=True))
    followed          = Column(Boolean, default=False)
    followed_at       = Column(TIMESTAMP(timezone=True))
    status            = Column(String(50), nullable=False, default="pending")
    error_message     = Column(Text)
    retry_count       = Column(Integer, default=0)
    notion_synced     = Column(Boolean, default=False)
    notion_page_id    = Column(String(100))
    dm_message_id     = Column(String(100))
    processed_at      = Column(TIMESTAMP(timezone=True))
    created_at        = Column(TIMESTAMP(timezone=True), server_default="NOW()")
    updated_at        = Column(TIMESTAMP(timezone=True), server_default="NOW()")

    # Relationships using string targets to prevent circular dependency imports
    resources = relationship("DMResource", back_populates="reel", cascade="all, delete")
    logs      = relationship("ProcessLog", back_populates="reel")
