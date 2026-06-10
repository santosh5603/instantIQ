from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID

class ProcessLogBase(BaseModel):
    step_name: str
    status: str  # success | error | warning | info
    message: Optional[str] = None
    error_message: Optional[str] = None
    extra_metadata: Optional[Any] = None

class ProcessLogCreate(ProcessLogBase):
    reel_id: Optional[UUID] = None

class ProcessLogResponse(ProcessLogBase):
    id: UUID
    reel_id: Optional[UUID] = None
    timestamp: datetime

    class Config:
        from_attributes = True
