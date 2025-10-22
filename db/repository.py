from typing import Optional
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from db.models import Article, ArticleAnalysis, DataSource, AgingTheory, ArticleTheory
from prompt_schemas import ArticleClassificationResponse, AgingTheoryAnalysisResponse
from cost_tracker import CostInfo


class ArticleRepository:
    """Repository for Article CRUD operations"""
    
    @staticmethod
    async def check_exists_by_doi(db: AsyncSession, doi: str) -> bool:
        """
        Check if an article with given DOI already exists
        
        Args:
            db: Database session
            doi: Digital Object Identifier
            
        Returns:
            True if article exists, False otherwise
        """
        result = await db.execute(
            select(Article).where(Article.doi == doi)
        )
        article = result.scalar_one_or_none()
        return article is not None
    
    @staticmethod
    async def get_by_doi(db: AsyncSession, doi: str) -> Optional[Article]:
        """
        Get article by DOI
        
        Args:
            db: Database session
            doi: Digital Object Identifier
            
        Returns:
            Article object or None
        """
        result = await db.execute(
            select(Article).where(Article.doi == doi)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_id(db: AsyncSession, article_id: uuid.UUID) -> Optional[Article]:
        """
        Get article by ID with analyses
        
        Args:
            db: Database session
            article_id: Article UUID
            
        Returns:
            Article object or None
        """
        result = await db.execute(
            select(Article)
            .options(selectinload(Article.analyses))
            .where(Article.id == article_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create(
        db: AsyncSession,
        doi: str,
        title: str,
        abstract: str,
        source: str,
        classification: Optional[ArticleClassificationResponse] = None,
        year: Optional[int] = None,
        journal: Optional[str] = None,
        keywords: Optional[str] = None,
        full_text_url: Optional[str] = None,
        pdf_url: Optional[str] = None,
    ) -> Article:
        """
        Create a new article
        
        Args:
            db: Database session
            doi: Digital Object Identifier
            title: Article title
            abstract: Article abstract
            source: Source of the article (pubmed, pmc, etc.)
            classification: Classification result
            year: Publication year
            journal: Journal name
            keywords: Keywords (comma-separated)
            full_text_url: URL to full text
            pdf_url: URL to PDF
            
        Returns:
            Created Article object
        """
        article = Article(
            doi=doi,
            title=title,
            abstract=abstract,
            source=source,
            year=year,
            journal=journal,
            keywords=keywords,
            full_text_url=full_text_url,
            pdf_url=pdf_url,
        )
        
        # Add classification info if provided
        if classification:
            article.is_aging_related = (classification.is_aging_related == "yes")
            article.classification_confidence = classification.confidence
            article.classification_explanation = classification.explanation
        
        db.add(article)
        await db.flush()
        await db.refresh(article)
        
        logger.info(f"Created article: {article.title[:50]}... (DOI: {doi})")
        return article
    
    @staticmethod
    async def list_articles(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        source: Optional[str] = None,
        is_aging_related: Optional[bool] = None,
    ) -> list[Article]:
        """
        List articles with pagination and filters
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            source: Filter by source
            is_aging_related: Filter by aging classification
            
        Returns:
            List of Article objects
        """
        query = select(Article).order_by(Article.created_at.desc())
        
        if source:
            query = query.where(Article.source == source)
        if is_aging_related is not None:
            query = query.where(Article.is_aging_related == is_aging_related)
        
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def count_articles(
        db: AsyncSession,
        source: Optional[str] = None,
        is_aging_related: Optional[bool] = None,
    ) -> int:
        """
        Count articles with filters

        Args:
            db: Database session
            source: Filter by source
            is_aging_related: Filter by aging classification

        Returns:
            Count of articles
        """
        query = select(func.count(Article.id))

        if source:
            query = query.where(Article.source == source)
        if is_aging_related is not None:
            query = query.where(Article.is_aging_related == is_aging_related)

        result = await db.execute(query)
        return result.scalar_one()

    @staticmethod
    async def get_unanalyzed_with_pdfs(db: AsyncSession, limit: int = 100) -> list[Article]:
        """
        Get articles that have PDF URLs but haven't been analyzed yet

        Args:
            db: Database session
            limit: Maximum number of articles to return

        Returns:
            List of Article objects
        """
        # LEFT JOIN with analyses to find articles without analysis
        query = (
            select(Article)
            .outerjoin(ArticleAnalysis, Article.id == ArticleAnalysis.article_id)
            .where(Article.pdf_url.isnot(None))
            .where(Article.pdf_url != "")
            .where(ArticleAnalysis.id.is_(None))  # No analysis exists
            .order_by(Article.created_at.desc())
            .limit(limit)
        )

        result = await db.execute(query)
        return list(result.scalars().all())


class AnalysisRepository:
    """Repository for ArticleAnalysis CRUD operations"""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        article_id: uuid.UUID,
        analysis: AgingTheoryAnalysisResponse,
        full_text: str,
        cost_info: CostInfo,
    ) -> ArticleAnalysis:
        """
        Create article analysis
        
        Args:
            db: Database session
            article_id: Article UUID
            analysis: Analysis results
            full_text: Full text from PDF
            cost_info: Cost tracking info
            
        Returns:
            Created ArticleAnalysis object
        """
        article_analysis = ArticleAnalysis(
            article_id=article_id,
            full_text=full_text,
            q1_biomarker=analysis.q1_biomarker,
            q1_explanation=analysis.q1_explanation,
            q2_molecular_mechanism=analysis.q2_molecular_mechanism,
            q2_explanation=analysis.q2_explanation,
            q3_longevity_intervention=analysis.q3_longevity_intervention,
            q3_explanation=analysis.q3_explanation,
            q4_aging_irreversible=analysis.q4_aging_irreversible,
            q4_explanation=analysis.q4_explanation,
            q5_species_lifespan_biomarker=analysis.q5_species_lifespan_biomarker,
            q5_explanation=analysis.q5_explanation,
            q6_naked_mole_rat=analysis.q6_naked_mole_rat,
            q6_explanation=analysis.q6_explanation,
            q7_bird_longevity=analysis.q7_bird_longevity,
            q7_explanation=analysis.q7_explanation,
            q8_size_lifespan=analysis.q8_size_lifespan,
            q8_explanation=analysis.q8_explanation,
            q9_calorie_restriction=analysis.q9_calorie_restriction,
            q9_explanation=analysis.q9_explanation,
            analysis_cost={
                "input_tokens": cost_info.input_tokens,
                "output_tokens": cost_info.output_tokens,
                "total_tokens": cost_info.total_tokens,
                "input_cost_usd": cost_info.input_cost_usd,
                "output_cost_usd": cost_info.output_cost_usd,
                "total_cost_usd": cost_info.total_cost_usd,
                "model": cost_info.model,
            }
        )
        
        db.add(article_analysis)
        await db.flush()
        await db.refresh(article_analysis)
        
        logger.info(f"Created analysis for article_id: {article_id}")
        return article_analysis
    
    @staticmethod
    async def get_by_article_id(
        db: AsyncSession,
        article_id: uuid.UUID
    ) -> Optional[ArticleAnalysis]:
        """
        Get latest analysis for an article
        
        Args:
            db: Database session
            article_id: Article UUID
            
        Returns:
            ArticleAnalysis object or None
        """
        result = await db.execute(
            select(ArticleAnalysis)
            .where(ArticleAnalysis.article_id == article_id)
            .order_by(ArticleAnalysis.analyzed_at.desc())
        )
        return result.scalar_one_or_none()


class DataSourceRepository:
    """Repository for DataSource CRUD operations"""
    
    @staticmethod
    async def get_all(db: AsyncSession, active_only: bool = True) -> list[DataSource]:
        """
        Get all data sources
        
        Args:
            db: Database session
            active_only: Return only active sources
            
        Returns:
            List of DataSource objects
        """
        query = select(DataSource)
        
        if active_only:
            query = query.where(DataSource.is_active == True)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_name(db: AsyncSession, source_name: str) -> Optional[DataSource]:
        """
        Get data source by name
        
        Args:
            db: Database session
            source_name: Source name
            
        Returns:
            DataSource object or None
        """
        result = await db.execute(
            select(DataSource).where(DataSource.source_name == source_name)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_or_update(
        db: AsyncSession,
        source_name: str,
        display_name: str,
        requires_api_key: bool = False,
        api_client_class: Optional[str] = None,
        user_api_key: Optional[str] = None,
        is_active: bool = True,
        description: Optional[str] = None,
    ) -> DataSource:
        """
        Create or update data source
        
        Args:
            db: Database session
            source_name: Unique source name
            display_name: Display name
            requires_api_key: Whether API key is required
            api_client_class: API client class name
            user_api_key: User's API key
            is_active: Whether source is active
            description: Source description
            
        Returns:
            DataSource object
        """
        existing = await DataSourceRepository.get_by_name(db, source_name)
        
        if existing:
            # Update existing
            existing.display_name = display_name
            existing.requires_api_key = requires_api_key
            existing.api_client_class = api_client_class
            if user_api_key:
                existing.user_api_key = user_api_key
            existing.is_active = is_active
            if description:
                existing.description = description
            
            await db.flush()
            await db.refresh(existing)
            logger.info(f"Updated data source: {source_name}")
            return existing
        else:
            # Create new
            data_source = DataSource(
                source_name=source_name,
                display_name=display_name,
                requires_api_key=requires_api_key,
                api_client_class=api_client_class,
                user_api_key=user_api_key,
                is_active=is_active,
                description=description,
            )
            db.add(data_source)
            await db.flush()
            await db.refresh(data_source)
            logger.info(f"Created data source: {source_name}")
            return data_source
    
    @staticmethod
    async def set_api_key(
        db: AsyncSession,
        source_name: str,
        api_key: str
    ) -> Optional[DataSource]:
        """
        Set API key for a data source
        
        Args:
            db: Database session
            source_name: Source name
            api_key: API key to set
            
        Returns:
            Updated DataSource object or None
        """
        source = await DataSourceRepository.get_by_name(db, source_name)
        
        if source:
            source.user_api_key = api_key
            source.is_active = True
            await db.flush()
            await db.refresh(source)
            logger.info(f"Set API key for source: {source_name}")
            return source
        
        return None


class TheoryRepository:
    """Repository for AgingTheory CRUD operations"""
    
    @staticmethod
    async def find_by_name(db: AsyncSession, theory_name: str) -> Optional[AgingTheory]:
        """
        Find theory by exact name match
        
        Args:
            db: Database session
            theory_name: Theory name
            
        Returns:
            AgingTheory object or None
        """
        result = await db.execute(
            select(AgingTheory).where(AgingTheory.theory_name == theory_name)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_id(db: AsyncSession, theory_id: uuid.UUID) -> Optional[AgingTheory]:
        """
        Get theory by ID with related articles
        
        Args:
            db: Database session
            theory_id: Theory UUID
            
        Returns:
            AgingTheory object or None
        """
        result = await db.execute(
            select(AgingTheory)
            .options(selectinload(AgingTheory.article_theories))
            .where(AgingTheory.id == theory_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create(
        db: AsyncSession,
        theory_name: str,
        description: str,
        evidence_level: Optional[str] = None,
        category: Optional[str] = None,
        first_mentioned_in_article_id: Optional[uuid.UUID] = None,
    ) -> AgingTheory:
        """
        Create a new aging theory
        
        Args:
            db: Database session
            theory_name: Name of the theory
            description: Description of the theory
            evidence_level: weak/moderate/strong
            category: Category (nutritional/genetic/cellular/etc)
            first_mentioned_in_article_id: First article that mentioned this theory
            
        Returns:
            Created AgingTheory object
        """
        theory = AgingTheory(
            theory_name=theory_name,
            description=description,
            evidence_level=evidence_level,
            category=category,
            first_mentioned_in_article_id=first_mentioned_in_article_id,
            mention_count=1,
        )
        
        db.add(theory)
        await db.flush()
        await db.refresh(theory)
        
        logger.info(f"Created theory: {theory_name}")
        return theory
    
    @staticmethod
    async def increment_mention_count(db: AsyncSession, theory_id: uuid.UUID) -> None:
        """
        Increment mention count for a theory
        
        Args:
            db: Database session
            theory_id: Theory UUID
        """
        theory = await TheoryRepository.get_by_id(db, theory_id)
        if theory:
            theory.mention_count += 1
            await db.flush()
            logger.info(f"Incremented mention count for theory: {theory.theory_name}")
    
    @staticmethod
    async def list_theories(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        evidence_level: Optional[str] = None,
    ) -> list[AgingTheory]:
        """
        List theories with pagination and filters
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            category: Filter by category
            evidence_level: Filter by evidence level
            
        Returns:
            List of AgingTheory objects
        """
        query = select(AgingTheory).order_by(AgingTheory.mention_count.desc())
        
        if category:
            query = query.where(AgingTheory.category == category)
        if evidence_level:
            query = query.where(AgingTheory.evidence_level == evidence_level)
        
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def search_theories(db: AsyncSession, search_term: str, limit: int = 10) -> list[AgingTheory]:
        """
        Search theories by name or description
        
        Args:
            db: Database session
            search_term: Search term
            limit: Maximum number of results
            
        Returns:
            List of matching AgingTheory objects
        """
        search_pattern = f"%{search_term}%"
        result = await db.execute(
            select(AgingTheory)
            .where(
                (AgingTheory.theory_name.ilike(search_pattern)) |
                (AgingTheory.description.ilike(search_pattern))
            )
            .order_by(AgingTheory.mention_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class ArticleTheoryRepository:
    """Repository for ArticleTheory link operations"""
    
    @staticmethod
    async def create_link(
        db: AsyncSession,
        article_id: uuid.UUID,
        theory_id: uuid.UUID,
        relevance_score: Optional[float] = None,
        extracted_context: Optional[str] = None,
    ) -> ArticleTheory:
        """
        Create a link between article and theory
        
        Args:
            db: Database session
            article_id: Article UUID
            theory_id: Theory UUID
            relevance_score: How relevant is the theory to the article (0-1)
            extracted_context: Context from article where theory is mentioned
            
        Returns:
            Created ArticleTheory link
        """
        link = ArticleTheory(
            article_id=article_id,
            theory_id=theory_id,
            relevance_score=relevance_score,
            extracted_context=extracted_context,
        )
        
        db.add(link)
        await db.flush()
        await db.refresh(link)
        
        # Increment theory mention count
        await TheoryRepository.increment_mention_count(db, theory_id)
        
        logger.info(f"Linked article {article_id} with theory {theory_id}")
        return link
    
    @staticmethod
    async def get_theories_for_article(
        db: AsyncSession,
        article_id: uuid.UUID
    ) -> list[ArticleTheory]:
        """
        Get all theories linked to an article
        
        Args:
            db: Database session
            article_id: Article UUID
            
        Returns:
            List of ArticleTheory links with theory data
        """
        result = await db.execute(
            select(ArticleTheory)
            .options(selectinload(ArticleTheory.theory))
            .where(ArticleTheory.article_id == article_id)
            .order_by(ArticleTheory.relevance_score.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_articles_for_theory(
        db: AsyncSession,
        theory_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50
    ) -> list[ArticleTheory]:
        """
        Get all articles linked to a theory
        
        Args:
            db: Database session
            theory_id: Theory UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of ArticleTheory links with article data
        """
        result = await db.execute(
            select(ArticleTheory)
            .options(selectinload(ArticleTheory.article))
            .where(ArticleTheory.theory_id == theory_id)
            .order_by(ArticleTheory.relevance_score.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

