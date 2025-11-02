"""
Data models for DealRadar
Defines data structures and type hints for database operations
"""
from typing import TypedDict, List, Optional
from datetime import datetime


class PostData(TypedDict, total=False):
    """Type definition for post data"""
    ad_id: str
    title: str
    price: Optional[str]
    description: Optional[str]
    seller: Optional[str]
    location: Optional[str]
    category: Optional[str]
    company_ad: bool
    type: Optional[str]
    region: Optional[str]
    images: List[str]


class EvaluationData(TypedDict, total=False):
    """Type definition for evaluation data"""
    ad_id: str
    status: str  # 'pending', 'completed', 'error'
    value_score: Optional[int]
    evaluation_notes: Optional[str]
    error_message: Optional[str]
    evaluated_at: Optional[datetime]


class DatabaseStats(TypedDict):
    """Type definition for database statistics"""
    total_posts: int
    evaluated_posts: int
    pending_evaluations: int
    failed_evaluations: int
    high_value_deals: int
    avg_score: Optional[float]
