import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, JSON, Index, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Optional


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


class Article(Base):
    """
    Article model - stores research papers with deduplication by DOI
    """
    __tablename__ = "articles"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    doi: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str] = mapped_column(Text, nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=True)
    journal: Mapped[str] = mapped_column(String(500), nullable=True)
    keywords: Mapped[str] = mapped_column(Text, nullable=True)  # Comma-separated
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # pubmed, pmc, crawled_website
    full_text_url: Mapped[str] = mapped_column(String(1000), nullable=True)
    pdf_url: Mapped[str] = mapped_column(String(1000), nullable=True)
    
    # Classification info
    is_aging_related: Mapped[bool] = mapped_column(Boolean, default=True)
    classification_confidence: Mapped[str] = mapped_column(String(20), nullable=True)  # high, medium, low
    classification_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    # Relationships
    analyses: Mapped[list["ArticleAnalysis"]] = relationship(
        "ArticleAnalysis", 
        back_populates="article",
        cascade="all, delete-orphan"
    )
    article_theories: Mapped[list["ArticleTheory"]] = relationship(
        "ArticleTheory",
        back_populates="article",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_article_source', 'source'),
        Index('idx_article_year', 'year'),
        Index('idx_article_created_at', 'created_at'),
    )


class ArticleAnalysis(Base):
    """
    Article analysis model - stores detailed analysis results based on 9 questions
    """
    __tablename__ = "article_analyses"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("articles.id"),
        nullable=False, 
        index=True
    )
    
    # Full text from PDF
    full_text: Mapped[str] = mapped_column(Text, nullable=True)
    
    # 9 Questions Analysis Results
    q1_biomarker: Mapped[str] = mapped_column(String(10), nullable=True)  # Yes/No
    q1_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    
    q2_molecular_mechanism: Mapped[str] = mapped_column(String(10), nullable=True)
    q2_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    
    q3_longevity_intervention: Mapped[str] = mapped_column(String(10), nullable=True)
    q3_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    
    q4_aging_irreversible: Mapped[str] = mapped_column(String(10), nullable=True)
    q4_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    
    q5_species_lifespan_biomarker: Mapped[str] = mapped_column(String(10), nullable=True)
    q5_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    
    q6_naked_mole_rat: Mapped[str] = mapped_column(String(10), nullable=True)
    q6_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    
    q7_bird_longevity: Mapped[str] = mapped_column(String(10), nullable=True)
    q7_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    
    q8_size_lifespan: Mapped[str] = mapped_column(String(10), nullable=True)
    q8_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    
    q9_calorie_restriction: Mapped[str] = mapped_column(String(10), nullable=True)
    q9_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Review and actuality analysis
    review_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    citation_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    actuality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    controversy_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Cost tracking
    analysis_cost: Mapped[dict] = mapped_column(JSON, nullable=True)  # CostInfo as JSON
    
    # Timestamps
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    # Relationships
    article: Mapped["Article"] = relationship("Article", back_populates="analyses")
    
    __table_args__ = (
        Index('idx_analysis_article_id', 'article_id'),
        Index('idx_analysis_analyzed_at', 'analyzed_at'),
    )


class DataSource(Base):
    """
    Data source model - manages external data sources and their API requirements
    """
    __tablename__ = "data_sources"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    requires_api_key: Mapped[bool] = mapped_column(Boolean, default=False)
    api_client_class: Mapped[str] = mapped_column(String(200), nullable=True)  # e.g., "ScopusClient"
    user_api_key: Mapped[str] = mapped_column(String(500), nullable=True)  # TODO: encrypt in production
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    __table_args__ = (
        Index('idx_data_source_name', 'source_name'),
        Index('idx_data_source_active', 'is_active'),
    )


class AgingTheory(Base):
    """
    Aging theory model - stores theories about aging mechanisms
    """
    __tablename__ = "aging_theories"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    theory_name: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # weak/moderate/strong
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # nutritional/genetic/cellular/etc
    
    # First article that mentioned this theory
    first_mentioned_in_article_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id"),
        nullable=True
    )
    mention_count: Mapped[int] = mapped_column(Integer, default=1)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    article_theories: Mapped[list["ArticleTheory"]] = relationship(
        "ArticleTheory",
        back_populates="theory",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_theory_name', 'theory_name'),
        Index('idx_theory_category', 'category'),
        Index('idx_theory_evidence_level', 'evidence_level'),
    )


class ArticleTheory(Base):
    """
    Many-to-many relationship between articles and aging theories
    """
    __tablename__ = "article_theories"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("articles.id"),
        nullable=False,
        index=True
    )
    theory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("aging_theories.id"),
        nullable=False,
        index=True
    )
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extracted_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    # Relationships
    article: Mapped["Article"] = relationship("Article", back_populates="article_theories")
    theory: Mapped["AgingTheory"] = relationship("AgingTheory", back_populates="article_theories")
    
    __table_args__ = (
        Index('idx_article_theory_article_id', 'article_id'),
        Index('idx_article_theory_theory_id', 'theory_id'),
    )

