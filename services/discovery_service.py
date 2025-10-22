from typing import Optional
from loguru import logger

from article_classification import classify_article
from db.database import get_db
from db.repository import ArticleRepository
from task_queue.task_queue import TaskQueue


class DiscoveryService:
    """
    Service for discovering and classifying aging research papers
    """
    
    @staticmethod
    async def process_article(
        doi: str,
        title: str,
        abstract: str,
        source: str,
        year: Optional[int] = None,
        journal: Optional[str] = None,
        keywords: Optional[str] = None,
        full_text_url: Optional[str] = None,
        pdf_url: Optional[str] = None,
    ) -> dict:
        """
        Process a single article: classify, check duplicates, save, and enqueue
        
        Args:
            doi: Digital Object Identifier
            title: Article title
            abstract: Article abstract
            source: Source of the article (pubmed, pmc, etc.)
            year: Publication year
            journal: Journal name
            keywords: Keywords (comma-separated)
            full_text_url: URL to full text
            pdf_url: URL to PDF
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing article: {title[:50]}... (DOI: {doi})")
        
        # Step 1: Check if article already exists
        async with get_db() as db:
            exists = await ArticleRepository.check_exists_by_doi(db, doi)
            
            if exists:
                logger.info(f"Article already exists in database: {doi}")
                return {
                    "status": "skipped",
                    "reason": "duplicate",
                    "doi": doi,
                    "title": title,
                }
        
        # Step 2: Classify article using AI
        try:
            # Use empty string if abstract is None
            abstract_for_classification = abstract or ""
            
            # Skip classification if both title and abstract are empty
            if not title and not abstract_for_classification:
                logger.warning(f"Article {doi} has no title or abstract, skipping")
                return {
                    "status": "skipped",
                    "reason": "no_content",
                    "doi": doi,
                }
            
            classification, cost_info = await classify_article(title, abstract_for_classification)
            logger.info(
                f"Classification: {classification.is_aging_related} "
                f"(confidence: {classification.confidence})"
            )
        except Exception as e:
            logger.error(f"Failed to classify article {doi}: {e}")
            return {
                "status": "error",
                "reason": "classification_failed",
                "doi": doi,
                "error": str(e),
            }
        
        # Step 3: Only proceed if aging-related
        if classification.is_aging_related != "yes":
            logger.info(f"Article not aging-related, skipping: {doi}")
            return {
                "status": "skipped",
                "reason": "not_aging_related",
                "doi": doi,
                "classification": classification.dict(),
            }
        
        # Step 4: Save article to database
        try:
            async with get_db() as db:
                article = await ArticleRepository.create(
                    db=db,
                    doi=doi,
                    title=title,
                    abstract=abstract,
                    source=source,
                    classification=classification,
                    year=year,
                    journal=journal,
                    keywords=keywords,
                    full_text_url=full_text_url,
                    pdf_url=pdf_url,
                )
                article_id = str(article.id)
        except Exception as e:
            logger.error(f"Failed to save article {doi}: {e}")
            return {
                "status": "error",
                "reason": "save_failed",
                "doi": doi,
                "error": str(e),
            }
        
        # Step 5: Enqueue for analysis if PDF is available
        if pdf_url:
            try:
                task_id = await TaskQueue.enqueue_article_task({
                    "article_id": article_id,
                    "doi": doi,
                    "title": title,
                    "abstract": abstract,
                    "pdf_url": pdf_url,
                })
                logger.info(f"Enqueued article for analysis: {task_id}")
                
                return {
                    "status": "success",
                    "article_id": article_id,
                    "doi": doi,
                    "task_id": task_id,
                    "classification": classification.dict(),
                    "cost": cost_info.total_cost_usd,
                }
            except Exception as e:
                logger.error(f"Failed to enqueue article {doi}: {e}")
                return {
                    "status": "partial_success",
                    "reason": "enqueue_failed",
                    "article_id": article_id,
                    "doi": doi,
                    "error": str(e),
                }
        else:
            logger.warning(f"No PDF URL available for article {doi}, skipping analysis queue")
            return {
                "status": "success",
                "article_id": article_id,
                "doi": doi,
                "classification": classification.dict(),
                "cost": cost_info.total_cost_usd,
                "note": "no_pdf_url",
            }
    
    @staticmethod
    async def process_articles_batch(articles: list[dict]) -> dict:
        """
        Process multiple articles in batch
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Summary of processing results
        """
        logger.info(f"Processing batch of {len(articles)} articles")
        
        results = {
            "total": len(articles),
            "success": 0,
            "skipped": 0,
            "errors": 0,
            "details": [],
        }
        
        for article_data in articles:
            try:
                result = await DiscoveryService.process_article(**article_data)
                results["details"].append(result)
                
                if result["status"] == "success":
                    results["success"] += 1
                elif result["status"] == "skipped":
                    results["skipped"] += 1
                else:
                    results["errors"] += 1
                    
            except Exception as e:
                logger.error(f"Unexpected error processing article: {e}")
                results["errors"] += 1
                results["details"].append({
                    "status": "error",
                    "reason": "unexpected_error",
                    "error": str(e),
                })
        
        logger.info(
            f"Batch processing complete: {results['success']} success, "
            f"{results['skipped']} skipped, {results['errors']} errors"
        )
        
        return results

