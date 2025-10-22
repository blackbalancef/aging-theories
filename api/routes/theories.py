import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from db.database import get_db
from db.repository import TheoryRepository, ArticleTheoryRepository

router = APIRouter(prefix="/theories", tags=["theories"])


# Schemas
class TheoryResponse(BaseModel):
    """Theory response model"""
    id: str
    theory_name: str
    description: str
    evidence_level: Optional[str]
    category: Optional[str]
    mention_count: int
    
    class Config:
        from_attributes = True


class TheoryDetailResponse(TheoryResponse):
    """Detailed theory response with articles"""
    first_mentioned_in_article_id: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class ArticleTheoryResponse(BaseModel):
    """Article-Theory link response"""
    id: str
    article_id: str
    theory_id: str
    relevance_score: Optional[float]
    extracted_context: Optional[str]
    
    class Config:
        from_attributes = True


# Endpoints
@router.get("/", response_model=list[TheoryResponse])
async def list_theories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    category: Optional[str] = None,
    evidence_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all aging theories with pagination and filters
    
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    - **category**: Filter by category (nutritional, genetic, cellular, etc.)
    - **evidence_level**: Filter by evidence level (weak, moderate, strong)
    """
    theories = await TheoryRepository.list_theories(
        db,
        skip=skip,
        limit=limit,
        category=category,
        evidence_level=evidence_level
    )
    
    return [
        TheoryResponse(
            id=str(theory.id),
            theory_name=theory.theory_name,
            description=theory.description,
            evidence_level=theory.evidence_level,
            category=theory.category,
            mention_count=theory.mention_count
        )
        for theory in theories
    ]


@router.get("/search")
async def search_theories(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Search theories by name or description
    
    - **q**: Search query
    - **limit**: Maximum number of results
    """
    theories = await TheoryRepository.search_theories(db, q, limit)
    
    return [
        TheoryResponse(
            id=str(theory.id),
            theory_name=theory.theory_name,
            description=theory.description,
            evidence_level=theory.evidence_level,
            category=theory.category,
            mention_count=theory.mention_count
        )
        for theory in theories
    ]


@router.get("/{theory_id}", response_model=TheoryDetailResponse)
async def get_theory(
    theory_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific theory
    
    - **theory_id**: UUID of the theory
    """
    try:
        theory_uuid = uuid.UUID(theory_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid theory ID format")
    
    theory = await TheoryRepository.get_by_id(db, theory_uuid)
    
    if not theory:
        raise HTTPException(status_code=404, detail="Theory not found")
    
    return TheoryDetailResponse(
        id=str(theory.id),
        theory_name=theory.theory_name,
        description=theory.description,
        evidence_level=theory.evidence_level,
        category=theory.category,
        mention_count=theory.mention_count,
        first_mentioned_in_article_id=str(theory.first_mentioned_in_article_id) if theory.first_mentioned_in_article_id else None,
        created_at=theory.created_at.isoformat(),
        updated_at=theory.updated_at.isoformat()
    )


@router.get("/{theory_id}/articles")
async def get_theory_articles(
    theory_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all articles linked to a specific theory
    
    - **theory_id**: UUID of the theory
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    try:
        theory_uuid = uuid.UUID(theory_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid theory ID format")
    
    # Check if theory exists
    theory = await TheoryRepository.get_by_id(db, theory_uuid)
    if not theory:
        raise HTTPException(status_code=404, detail="Theory not found")
    
    # Get articles
    article_theories = await ArticleTheoryRepository.get_articles_for_theory(
        db,
        theory_uuid,
        skip=skip,
        limit=limit
    )
    
    return {
        "theory_id": theory_id,
        "theory_name": theory.theory_name,
        "total_articles": theory.mention_count,
        "articles": [
            {
                "article_id": str(at.article_id),
                "article_title": at.article.title if at.article else None,
                "article_doi": at.article.doi if at.article else None,
                "relevance_score": at.relevance_score,
                "extracted_context": at.extracted_context[:200] + "..." if at.extracted_context and len(at.extracted_context) > 200 else at.extracted_context,
                "linked_at": at.created_at.isoformat()
            }
            for at in article_theories
        ]
    }


@router.get("/stats/summary")
async def get_theories_stats(db: AsyncSession = Depends(get_db)):
    """Get summary statistics about theories"""
    all_theories = await TheoryRepository.list_theories(db, skip=0, limit=1000)
    
    # Calculate stats
    categories = {}
    evidence_levels = {}
    
    for theory in all_theories:
        # Count by category
        cat = theory.category or "unknown"
        categories[cat] = categories.get(cat, 0) + 1
        
        # Count by evidence level
        ev = theory.evidence_level or "unknown"
        evidence_levels[ev] = evidence_levels.get(ev, 0) + 1
    
    # Top mentioned theories
    top_theories = sorted(all_theories, key=lambda t: t.mention_count, reverse=True)[:10]
    
    return {
        "total_theories": len(all_theories),
        "total_mentions": sum(t.mention_count for t in all_theories),
        "categories": categories,
        "evidence_levels": evidence_levels,
        "top_theories": [
            {
                "id": str(t.id),
                "name": t.theory_name,
                "mention_count": t.mention_count,
                "category": t.category
            }
            for t in top_theories
        ]
    }

