from sqlalchemy import Column, String, Boolean, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base
import uuid

class CreatorRelationship(Base):
    __tablename__ = "creator_relationships"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_name     = Column(String(255), nullable=False, unique=True)
    followed         = Column(Boolean, default=False)
    followed_at      = Column(TIMESTAMP(timezone=True))
    unfollowed_at    = Column(TIMESTAMP(timezone=True))
    blocked          = Column(Boolean, default=False)
    purpose          = Column(Text)  # reel_id that triggered the follow
    last_interaction = Column(TIMESTAMP(timezone=True))
    total_reels      = Column(Integer, default=0)
    total_resources  = Column(Integer, default=0)
    created_at       = Column(TIMESTAMP(timezone=True), server_default="NOW()")
    updated_at       = Column(TIMESTAMP(timezone=True), server_default="NOW()")
