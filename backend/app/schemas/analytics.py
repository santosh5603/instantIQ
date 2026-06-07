from pydantic import BaseModel
from typing import List, Dict

class CategoryCount(BaseModel):
    category: str
    count: int

class StatusCount(BaseModel):
    status: str
    count: int

class ConversionStats(BaseModel):
    total_reels: int
    completed_reels: int
    failed_reels: int
    conversion_rate: float

class QueueMetrics(BaseModel):
    reels_queue_length: int
    notion_queue_length: int
    dlq_queue_length: int

class AnalyticsResponse(BaseModel):
    overall_conversion: ConversionStats
    status_distribution: List[StatusCount]
    category_distribution: List[CategoryCount]
    queue_metrics: QueueMetrics
    total_resources: int
    total_creators_followed: int
