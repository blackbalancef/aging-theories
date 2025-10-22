from typing import Optional
from datetime import datetime
from io import StringIO
import csv

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger

from db.database import get_db
from db.models import Article, ArticleAnalysis, AgingTheory, ArticleTheory


router = APIRouter(tags=["export"])


@router.get("/export/articles")
async def export_articles_to_csv(
    source: Optional[str] = Query(None, description="Filter by source"),
    is_aging_related: Optional[bool] = Query(None, description="Filter by aging relevance"),
    limit: int = Query(1000, le=10000, description="Maximum records to export"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export articles to CSV file
    
    Downloads articles data as CSV with all metadata:
    - DOI, title, abstract
    - Year, journal, keywords
    - Source, URLs
    - Classification info
    """
    logger.info(f"Exporting articles to CSV (source={source}, is_aging_related={is_aging_related}, limit={limit})")
    
    # Build query
    query = select(Article).order_by(Article.created_at.desc()).limit(limit)
    
    if source:
        query = query.where(Article.source == source)
    if is_aging_related is not None:
        query = query.where(Article.is_aging_related == is_aging_related)
    
    # Fetch articles
    result = await db.execute(query)
    articles = result.scalars().all()
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "DOI",
        "Title",
        "Abstract",
        "Year",
        "Journal",
        "Keywords",
        "Source",
        "Full Text URL",
        "PDF URL",
        "Is Aging Related",
        "Classification Confidence",
        "Classification Explanation",
        "Created At",
    ])
    
    # Write data
    for article in articles:
        writer.writerow([
            article.doi,
            article.title,
            article.abstract or "",
            article.year or "",
            article.journal or "",
            article.keywords or "",
            article.source,
            article.full_text_url or "",
            article.pdf_url or "",
            "Yes" if article.is_aging_related else "No",
            article.classification_confidence or "",
            article.classification_explanation or "",
            article.created_at.isoformat() if article.created_at else "",
        ])
    
    # Prepare response
    output.seek(0)
    filename = f"articles_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
    
    logger.info(f"Exported {len(articles)} articles to CSV")
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/analyses")
async def export_analyses_to_csv(
    limit: int = Query(1000, le=10000, description="Maximum records to export"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export article analyses to CSV file
    
    Downloads detailed analysis results including:
    - Article info (DOI, title)
    - All 9 questions and answers
    - Theories mentioned
    - Analysis costs
    """
    logger.info(f"Exporting analyses to CSV (limit={limit})")
    
    # Fetch analyses with article data
    query = (
        select(ArticleAnalysis)
        .options(selectinload(ArticleAnalysis.article))
        .order_by(ArticleAnalysis.analyzed_at.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    analyses = result.scalars().all()
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Article DOI",
        "Article Title",
        "Article Year",
        "Q1 Biomarker",
        "Q1 Explanation",
        "Q2 Molecular Mechanism",
        "Q2 Explanation",
        "Q3 Longevity Intervention",
        "Q3 Explanation",
        "Q4 Aging Irreversible",
        "Q4 Explanation",
        "Q5 Species Lifespan Biomarker",
        "Q5 Explanation",
        "Q6 Naked Mole Rat",
        "Q6 Explanation",
        "Q7 Bird Longevity",
        "Q7 Explanation",
        "Q8 Size Lifespan",
        "Q8 Explanation",
        "Q9 Calorie Restriction",
        "Q9 Explanation",
        "Review Summary",
        "Actuality Score",
        "Controversy Level",
        "Analysis Cost (USD)",
        "Analyzed At",
    ])
    
    # Write data
    for analysis in analyses:
        article = analysis.article
        cost = analysis.analysis_cost or {}
        
        writer.writerow([
            article.doi,
            article.title,
            article.year or "",
            analysis.q1_biomarker or "",
            analysis.q1_explanation or "",
            analysis.q2_molecular_mechanism or "",
            analysis.q2_explanation or "",
            analysis.q3_longevity_intervention or "",
            analysis.q3_explanation or "",
            analysis.q4_aging_irreversible or "",
            analysis.q4_explanation or "",
            analysis.q5_species_lifespan_biomarker or "",
            analysis.q5_explanation or "",
            analysis.q6_naked_mole_rat or "",
            analysis.q6_explanation or "",
            analysis.q7_bird_longevity or "",
            analysis.q7_explanation or "",
            analysis.q8_size_lifespan or "",
            analysis.q8_explanation or "",
            analysis.q9_calorie_restriction or "",
            analysis.q9_explanation or "",
            analysis.review_summary or "",
            analysis.actuality_score or "",
            analysis.controversy_level or "",
            f"${cost.get('total_cost_usd', 0):.4f}",
            analysis.analyzed_at.isoformat() if analysis.analyzed_at else "",
        ])
    
    # Prepare response
    output.seek(0)
    filename = f"analyses_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
    
    logger.info(f"Exported {len(analyses)} analyses to CSV")
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/theories")
async def export_theories_to_csv(
    category: Optional[str] = Query(None, description="Filter by category"),
    evidence_level: Optional[str] = Query(None, description="Filter by evidence level"),
    limit: int = Query(1000, le=10000, description="Maximum records to export"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export aging theories to CSV file
    
    Downloads theories data including:
    - Theory name and description
    - Category and evidence level
    - Mention count
    - First mentioned article
    """
    logger.info(f"Exporting theories to CSV (category={category}, evidence_level={evidence_level}, limit={limit})")
    
    # Build query
    query = (
        select(AgingTheory)
        .order_by(AgingTheory.mention_count.desc())
        .limit(limit)
    )
    
    if category:
        query = query.where(AgingTheory.category == category)
    if evidence_level:
        query = query.where(AgingTheory.evidence_level == evidence_level)
    
    # Fetch theories
    result = await db.execute(query)
    theories = result.scalars().all()
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Theory Name",
        "Description",
        "Category",
        "Evidence Level",
        "Mention Count",
        "Created At",
    ])
    
    # Write data
    for theory in theories:
        writer.writerow([
            theory.theory_name,
            theory.description,
            theory.category or "",
            theory.evidence_level or "",
            theory.mention_count,
            theory.created_at.isoformat() if theory.created_at else "",
        ])
    
    # Prepare response
    output.seek(0)
    filename = f"theories_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
    
    logger.info(f"Exported {len(theories)} theories to CSV")
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/article-theories")
async def export_article_theories_to_csv(
    limit: int = Query(5000, le=50000, description="Maximum records to export"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export article-theory relationships to CSV file
    
    Downloads the many-to-many relationships between articles and theories:
    - Article DOI and title
    - Theory name
    - Relevance score
    - Extracted context
    """
    logger.info(f"Exporting article-theory relationships to CSV (limit={limit})")
    
    # Fetch relationships with article and theory data
    query = (
        select(ArticleTheory)
        .options(
            selectinload(ArticleTheory.article),
            selectinload(ArticleTheory.theory)
        )
        .order_by(ArticleTheory.created_at.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    relationships = result.scalars().all()
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Article DOI",
        "Article Title",
        "Article Year",
        "Theory Name",
        "Theory Category",
        "Theory Evidence Level",
        "Relevance Score",
        "Extracted Context",
        "Created At",
    ])
    
    # Write data
    for rel in relationships:
        article = rel.article
        theory = rel.theory
        
        writer.writerow([
            article.doi,
            article.title,
            article.year or "",
            theory.theory_name,
            theory.category or "",
            theory.evidence_level or "",
            f"{rel.relevance_score:.2f}" if rel.relevance_score else "",
            rel.extracted_context or "",
            rel.created_at.isoformat() if rel.created_at else "",
        ])
    
    # Prepare response
    output.seek(0)
    filename = f"article_theories_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
    
    logger.info(f"Exported {len(relationships)} article-theory relationships to CSV")
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/full")
async def export_full_dataset_to_csv(
    limit: int = Query(1000, le=5000, description="Maximum articles to export"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export complete dataset with articles, analyses, and theories
    
    Downloads comprehensive data combining:
    - Article metadata
    - Analysis results (9 questions)
    - All theories mentioned in each article
    
    Warning: This can be a large file for many articles
    """
    logger.info(f"Exporting full dataset to CSV (limit={limit})")
    
    # Fetch articles with analyses and theories
    query = (
        select(Article)
        .options(
            selectinload(Article.analyses),
            selectinload(Article.article_theories).selectinload(ArticleTheory.theory)
        )
        .order_by(Article.created_at.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    articles = result.scalars().all()
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Article DOI",
        "Article Title",
        "Abstract",
        "Year",
        "Journal",
        "Keywords",
        "Source",
        "Is Aging Related",
        "Analyzed",
        "Theories Mentioned",
        "Q1 Biomarker",
        "Q2 Molecular Mechanism",
        "Q3 Longevity Intervention",
        "Q4 Aging Irreversible",
        "Q5 Species Lifespan Biomarker",
        "Q6 Naked Mole Rat",
        "Q7 Bird Longevity",
        "Q8 Size Lifespan",
        "Q9 Calorie Restriction",
        "Analysis Cost (USD)",
        "Created At",
    ])
    
    # Write data
    for article in articles:
        # Get analysis if exists
        analysis = article.analyses[0] if article.analyses else None
        
        # Get theories
        theories = [at.theory.theory_name for at in article.article_theories]
        theories_str = "; ".join(theories) if theories else ""
        
        # Get cost
        cost = 0.0
        if analysis and analysis.analysis_cost:
            cost = analysis.analysis_cost.get('total_cost_usd', 0.0)
        
        writer.writerow([
            article.doi,
            article.title,
            article.abstract or "",
            article.year or "",
            article.journal or "",
            article.keywords or "",
            article.source,
            "Yes" if article.is_aging_related else "No",
            "Yes" if analysis else "No",
            theories_str,
            analysis.q1_biomarker if analysis else "",
            analysis.q2_molecular_mechanism if analysis else "",
            analysis.q3_longevity_intervention if analysis else "",
            analysis.q4_aging_irreversible if analysis else "",
            analysis.q5_species_lifespan_biomarker if analysis else "",
            analysis.q6_naked_mole_rat if analysis else "",
            analysis.q7_bird_longevity if analysis else "",
            analysis.q8_size_lifespan if analysis else "",
            analysis.q9_calorie_restriction if analysis else "",
            f"${cost:.4f}",
            article.created_at.isoformat() if article.created_at else "",
        ])
    
    # Prepare response
    output.seek(0)
    filename = f"full_dataset_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
    
    logger.info(f"Exported full dataset with {len(articles)} articles to CSV")
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

