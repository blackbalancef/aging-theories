from fastapi import APIRouter
from sqlalchemy import select, func
from loguru import logger

from db.database import get_db
from db.models import Article, ArticleAnalysis
from api.schemas import CostSummaryResponse

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("/summary", response_model=CostSummaryResponse)
async def get_cost_summary():
    """
    Get overall cost summary for all AI operations
    """
    async with get_db() as db:
        # Count total articles
        total_articles_result = await db.execute(
            select(func.count(Article.id))
        )
        total_articles = total_articles_result.scalar_one()
        
        # Count total analyses
        total_analyses_result = await db.execute(
            select(func.count(ArticleAnalysis.id))
        )
        total_analyses = total_analyses_result.scalar_one()
        
        # Get all analyses with cost info
        analyses_result = await db.execute(
            select(ArticleAnalysis.analysis_cost)
            .where(ArticleAnalysis.analysis_cost.isnot(None))
        )
        analysis_costs = [cost for cost in analyses_result.scalars().all() if cost]
        
        # Calculate total analysis costs
        total_analysis_cost = sum(
            cost.get("total_cost_usd", 0.0)
            for cost in analysis_costs
        )
        
        # Estimate classification costs (assuming all articles were classified)
        # Average classification cost is much lower than analysis
        estimated_classification_cost_per_article = 0.0001  # $0.0001 per classification
        total_classification_cost = total_articles * estimated_classification_cost_per_article
        
        # Calculate totals
        total_cost = total_classification_cost + total_analysis_cost
        avg_cost_per_article = total_cost / total_articles if total_articles > 0 else 0.0
        avg_cost_per_analysis = total_analysis_cost / total_analyses if total_analyses > 0 else 0.0
    
    logger.info(
        f"Cost summary: {total_articles} articles, {total_analyses} analyses, "
        f"${total_cost:.4f} total cost"
    )
    
    return CostSummaryResponse(
        total_articles=total_articles,
        total_analyses=total_analyses,
        total_classification_cost=total_classification_cost,
        total_analysis_cost=total_analysis_cost,
        total_cost=total_cost,
        average_cost_per_article=avg_cost_per_article,
        average_cost_per_analysis=avg_cost_per_analysis,
    )


@router.get("/analyses/breakdown")
async def get_analyses_cost_breakdown():
    """
    Get detailed cost breakdown for all analyses
    """
    async with get_db() as db:
        analyses_result = await db.execute(
            select(
                ArticleAnalysis.id,
                ArticleAnalysis.article_id,
                ArticleAnalysis.analysis_cost,
                ArticleAnalysis.analyzed_at
            )
            .where(ArticleAnalysis.analysis_cost.isnot(None))
            .order_by(ArticleAnalysis.analyzed_at.desc())
        )
        
        analyses = analyses_result.all()
    
    breakdown = []
    for analysis in analyses:
        cost_info = analysis.analysis_cost
        if cost_info:
            breakdown.append({
                "analysis_id": str(analysis.id),
                "article_id": str(analysis.article_id),
                "analyzed_at": analysis.analyzed_at.isoformat(),
                "input_tokens": cost_info.get("input_tokens", 0),
                "output_tokens": cost_info.get("output_tokens", 0),
                "total_tokens": cost_info.get("total_tokens", 0),
                "cost_usd": cost_info.get("total_cost_usd", 0.0),
                "model": cost_info.get("model", "unknown"),
            })
    
    total_cost = sum(item["cost_usd"] for item in breakdown)
    total_tokens = sum(item["total_tokens"] for item in breakdown)
    
    return {
        "total_analyses": len(breakdown),
        "total_cost_usd": total_cost,
        "total_tokens": total_tokens,
        "average_cost_per_analysis": total_cost / len(breakdown) if breakdown else 0.0,
        "breakdown": breakdown,
    }

