from sqlalchemy import Column, String, ForeignKey, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base
import uuid

class ProcessLog(Base):
    __tablename__ = "process_logs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reel_id       = Column(UUID(as_uuid=True), ForeignKey("reels.id", ondelete="SET NULL"))
    step_name     = Column(String(100), nullable=False)
    status        = Column(String(50), nullable=False)  # success | error | warning | info
    message       = Column(Text)
    error_message = Column(Text)
    extra_metadata = Column(JSONB)  # extra info
    timestamp     = Column(TIMESTAMP(timezone=True), server_default="NOW()")

    reel = relationship("Reel", back_populates="logs")
