from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base
import uuid

class DMResource(Base):
    __tablename__ = "dm_resources"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reel_id         = Column(UUID(as_uuid=True), ForeignKey("reels.id", ondelete="CASCADE"), nullable=False)
    resource_type   = Column(String(50), nullable=False)  # link, pdf, text, media, unknown
    resource_url    = Column(Text)
    resource_text   = Column(Text)
    attachment_path = Column(Text)  # Supabase Storage path
    file_name       = Column(Text)
    file_size_bytes = Column(Integer)
    category        = Column(String(100), default="Other")  # AI, Career, Programming, Fitness, Communication, Other
    notion_page_id  = Column(String(100))
    notion_synced   = Column(Boolean, default=False)
    received_at     = Column(TIMESTAMP(timezone=True), server_default="NOW()")
    created_at      = Column(TIMESTAMP(timezone=True), server_default="NOW()")

    reel = relationship("Reel", back_populates="resources")
