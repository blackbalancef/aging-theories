from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


# Article schemas
class ArticleBase(BaseModel):
    """Base article schema"""
    doi: str
    title: str
    abstract: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    keywords: Optional[str] = None
    source: str
    full_text_url: Optional[str] = None
    pdf_url: Optional[str] = None


class ArticleCreate(ArticleBase):
    """Schema for creating an article"""
    pass


class ArticleResponse(ArticleBase):
    """Schema for article response"""
    id: uuid.UUID
    is_aging_related: bool
    classification_confidence: Optional[str] = None
    classification_explanation: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    """Schema for paginated article list"""
    total: int
    items: List[ArticleResponse]
    page: int
    page_size: int


# Analysis schemas
class AnalysisResponse(BaseModel):
    """Schema for article analysis response"""
    id: uuid.UUID
    article_id: uuid.UUID
    
    q1_biomarker: Optional[str] = None
    q1_explanation: Optional[str] = None
    q2_molecular_mechanism: Optional[str] = None
    q2_explanation: Optional[str] = None
    q3_longevity_intervention: Optional[str] = None
    q3_explanation: Optional[str] = None
    q4_aging_irreversible: Optional[str] = None
    q4_explanation: Optional[str] = None
    q5_species_lifespan_biomarker: Optional[str] = None
    q5_explanation: Optional[str] = None
    q6_naked_mole_rat: Optional[str] = None
    q6_explanation: Optional[str] = None
    q7_bird_longevity: Optional[str] = None
    q7_explanation: Optional[str] = None
    q8_size_lifespan: Optional[str] = None
    q8_explanation: Optional[str] = None
    q9_calorie_restriction: Optional[str] = None
    q9_explanation: Optional[str] = None
    
    analysis_cost: Optional[dict] = None
    analyzed_at: datetime
    
    class Config:
        from_attributes = True


# Discovery schemas
class DiscoveryRequest(BaseModel):
    """Schema for starting discovery"""
    sources: Optional[List[str]] = Field(default=["pubmed", "pmc"], description="Sources to search")
    max_papers: int = Field(default=10, ge=1, le=1000, description="Maximum papers to retrieve")
    queries: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class DiscoveryResponse(BaseModel):
    """Schema for discovery response"""
    task_id: str
    status: str
    message: str


# Data source schemas
class DataSourceResponse(BaseModel):
    """Schema for data source response"""
    id: uuid.UUID
    source_name: str
    display_name: str
    requires_api_key: bool
    is_active: bool
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DataSourceApiKeyRequest(BaseModel):
    """Schema for setting API key"""
    api_key: str = Field(..., min_length=1, description="API key for the data source")


# Queue schemas
class QueueStatsResponse(BaseModel):
    """Schema for queue statistics"""
    queue_name: str
    queue_length: int
    total_connections: int
    total_commands: int


# Cost schemas
class CostSummaryResponse(BaseModel):
    """Schema for cost summary"""
    total_articles: int
    total_analyses: int
    total_classification_cost: float
    total_analysis_cost: float
    total_cost: float
    average_cost_per_article: float
    average_cost_per_analysis: float

