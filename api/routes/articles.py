from typing import Optional
import uuid
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from db.database import get_db
from db.repository import ArticleRepository, AnalysisRepository, ArticleTheoryRepository
from api.schemas import ArticleResponse, ArticleListResponse, AnalysisResponse
from task_queue.task_queue import TaskQueue

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    source: Optional[str] = Query(default=None, description="Filter by source"),
    is_aging_related: Optional[bool] = Query(default=None, description="Filter by aging classification"),
):
    """
    List articles with pagination and filters
    """
    skip = (page - 1) * page_size
    
    async with get_db() as db:
        articles = await ArticleRepository.list_articles(
            db=db,
            skip=skip,
            limit=page_size,
            source=source,
            is_aging_related=is_aging_related,
        )
        
        total = await ArticleRepository.count_articles(
            db=db,
            source=source,
            is_aging_related=is_aging_related,
        )
    
    return ArticleListResponse(
        total=total,
        items=[ArticleResponse.model_validate(article) for article in articles],
        page=page,
        page_size=page_size,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: uuid.UUID):
    """
    Get article by ID
    """
    async with get_db() as db:
        article = await ArticleRepository.get_by_id(db, article_id)
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
    
    return ArticleResponse.model_validate(article)


@router.get("/{article_id}/analysis", response_model=AnalysisResponse)
async def get_article_analysis(article_id: uuid.UUID):
    """
    Get analysis for an article
    """
    async with get_db() as db:
        # Check if article exists
        article = await ArticleRepository.get_by_id(db, article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Get analysis
        analysis = await AnalysisRepository.get_by_article_id(db, article_id)
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail="Analysis not found for this article"
            )
    
    return AnalysisResponse.model_validate(analysis)


@router.post("/{article_id}/reanalyze")
async def reanalyze_article(article_id: uuid.UUID):
    """
    Re-queue an article for analysis
    """
    async with get_db() as db:
        article = await ArticleRepository.get_by_id(db, article_id)
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        if not article.pdf_url:
            raise HTTPException(
                status_code=400,
                detail="Article has no PDF URL, cannot analyze"
            )
    
    # Enqueue for analysis
    task_id = await TaskQueue.enqueue_article_task({
        "article_id": str(article.id),
        "doi": article.doi,
        "title": article.title,
        "abstract": article.abstract,
        "pdf_url": article.pdf_url,
    })
    
    logger.info(f"Re-queued article {article_id} for analysis (task: {task_id})")
    
    return {
        "status": "success",
        "message": "Article queued for re-analysis",
        "task_id": task_id,
        "article_id": str(article_id),
    }


@router.get("/{article_id}/theories")
async def get_article_theories(article_id: uuid.UUID):
    """
    Get all theories linked to an article
    """
    async with get_db() as db:
        # Check if article exists
        article = await ArticleRepository.get_by_id(db, article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Get linked theories
        article_theories = await ArticleTheoryRepository.get_theories_for_article(db, article_id)
    
    return {
        "article_id": str(article_id),
        "article_title": article.title,
        "theories": [
            {
                "theory_id": str(at.theory_id),
                "theory_name": at.theory.theory_name if at.theory else None,
                "theory_description": at.theory.description if at.theory else None,
                "theory_category": at.theory.category if at.theory else None,
                "relevance_score": at.relevance_score,
                "extracted_context": at.extracted_context[:300] + "..." if at.extracted_context and len(at.extracted_context) > 300 else at.extracted_context,
            }
            for at in article_theories
        ]
    }

