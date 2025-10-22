import uuid
import json
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from loguru import logger

from db.database import get_db
from db.repository import (
    ArticleRepository,
    TheoryRepository,
    ArticleTheoryRepository
)
from article_classification import classify_article
from task_queue.task_queue import TaskQueue


@tool
async def check_article_exists(doi: str) -> str:
    """
    Check if an article with given DOI already exists in the database.
    
    Args:
        doi: Digital Object Identifier of the article
        
    Returns:
        String indicating if article exists
    """
    try:
        async with get_db() as db:
            exists = await ArticleRepository.check_exists_by_doi(db, doi)
            
        if exists:
            logger.info(f"Article exists in database: {doi}")
            return f"Article with DOI {doi} already exists in database. Skip processing."
        else:
            return f"Article with DOI {doi} does not exist. Can proceed with processing."
            
    except Exception as e:
        logger.error(f"Error checking article existence: {e}")
        return f"Error checking database: {str(e)}"


@tool
async def save_article(article_data: str) -> str:
    """
    Save a new article to the database after classification.
    Article data should be a JSON string with fields:
    doi, title, abstract, source, year (optional), journal (optional), 
    keywords (optional), full_text_url (optional), pdf_url (optional)
    
    Args:
        article_data: JSON string containing article information
        
    Returns:
        String with article_id and status
    """
    try:
        # Parse article data
        data = json.loads(article_data)
        
        doi = data.get('doi')
        title = data.get('title')
        abstract = data.get('abstract', '')
        source = data.get('source', 'web_crawl')
        
        if not doi or not title:
            return "Error: Missing required fields (doi or title)"
        
        logger.info(f"📝 Processing article: {title[:60]}...")
        
        # Check if already exists
        logger.debug(f"🔍 Checking if article exists: {doi}")
        async with get_db() as db:
            exists = await ArticleRepository.check_exists_by_doi(db, doi)
            if exists:
                logger.info(f"⏭️  Article already exists in DB: {doi}")
                return f"Article already exists: {doi}"
        
        # Classify article
        logger.info(f"🤖 Classifying article (AI)...")
        classification, cost_info = await classify_article(title, abstract)
        logger.info(f"✓ Classification: {classification.is_aging_related} (confidence: {classification.confidence})")
        
        if classification.is_aging_related != "yes":
            logger.info(f"⏭️  Article not aging-related, skipping: {doi}")
            return f"Article not aging-related (confidence: {classification.confidence}). Not saved."
        
        # Save to database
        logger.info(f"💾 Saving article to database...")
        async with get_db() as db:
            # Convert keywords list to comma-separated string if it's a list
            keywords = data.get('keywords')
            if isinstance(keywords, list):
                keywords = ', '.join(keywords) if keywords else None
            
            article = await ArticleRepository.create(
                db=db,
                doi=doi,
                title=title,
                abstract=abstract,
                source=source,
                classification=classification,
                year=data.get('year'),
                journal=data.get('journal'),
                keywords=keywords,
                full_text_url=data.get('full_text_url'),
                pdf_url=data.get('pdf_url'),
            )
            article_id = str(article.id)
            await db.commit()
        
        logger.info(f"✓ Article saved to DB: {article_id}")
        
        # Add to analysis queue
        logger.info(f"📤 Adding article to Redis analysis queue...")
        try:
            task_id = await TaskQueue.enqueue_article_task({
                "article_id": article_id,
                "doi": doi,
                "title": title,
                "abstract": abstract,
                "pdf_url": data.get('pdf_url')
            })
            queue_status = f" ✓ Enqueued for analysis (task: {task_id[:8]}...)"
            logger.info(f"Article {article_id} added to analysis queue with task {task_id}")
        except Exception as e:
            queue_status = f" ⚠ Failed to enqueue: {str(e)}"
            logger.warning(f"Failed to enqueue article for analysis: {e}")
        
        logger.info(f"Saved article: {article_id} ({doi})")
        return (
            f"Article saved successfully!\n"
            f"Article ID: {article_id}\n"
            f"DOI: {doi}\n"
            f"Classification: {classification.is_aging_related} "
            f"(confidence: {classification.confidence})\n"
            f"Cost: ${cost_info.total_cost_usd:.6f}\n"
            f"{queue_status}"
        )
        
    except json.JSONDecodeError as e:
        return f"Error parsing article data JSON: {str(e)}"
    except Exception as e:
        logger.error(f"Error saving article: {e}")
        return f"Error saving article: {str(e)}"


@tool
async def find_similar_theory(theory_name: str, description: str) -> str:
    """
    Search for existing theories similar to the given theory.
    
    Args:
        theory_name: Name of the theory to search for
        description: Description of the theory for additional matching
        
    Returns:
        String with found theories or indication that no match exists
    """
    try:
        async with get_db() as db:
            # First try exact name match
            theory = await TheoryRepository.find_by_name(db, theory_name)
            
            if theory:
                return (
                    f"Exact theory match found!\n"
                    f"Theory ID: {theory.id}\n"
                    f"Name: {theory.theory_name}\n"
                    f"Description: {theory.description}\n"
                    f"Category: {theory.category}\n"
                    f"Evidence Level: {theory.evidence_level}\n"
                    f"Mentions: {theory.mention_count}"
                )
            
            # Try search by keywords
            theories = await TheoryRepository.search_theories(db, theory_name, limit=5)
            
            if theories:
                results = []
                for t in theories:
                    results.append(
                        f"- {t.theory_name} (ID: {t.id})\n"
                        f"  {t.description[:100]}...\n"
                        f"  Category: {t.category}, Mentions: {t.mention_count}"
                    )
                
                return (
                    f"Found {len(theories)} similar theories:\n\n" +
                    "\n\n".join(results) +
                    "\n\nReview these to determine if any match your theory."
                )
            
            return f"No similar theories found for '{theory_name}'. You can create a new one."
            
    except Exception as e:
        logger.error(f"Error searching theories: {e}")
        return f"Error searching theories: {str(e)}"


@tool
async def create_theory(theory_data: str) -> str:
    """
    Create a new aging theory in the database.
    Theory data should be a JSON string with fields:
    theory_name, description, evidence_level (weak/moderate/strong),
    category (nutritional/genetic/cellular/etc), article_id (optional)
    
    Args:
        theory_data: JSON string containing theory information
        
    Returns:
        String with theory_id and status
    """
    try:
        data = json.loads(theory_data)
        
        theory_name = data.get('theory_name')
        description = data.get('description')
        
        if not theory_name or not description:
            return "Error: Missing required fields (theory_name or description)"
        
        # Check if theory already exists
        async with get_db() as db:
            existing = await TheoryRepository.find_by_name(db, theory_name)
            if existing:
                return (
                    f"Theory already exists: {theory_name} (ID: {existing.id})\n"
                    f"Use this theory_id to link articles instead of creating new."
                )
            
            # Create theory
            article_id = data.get('article_id')
            if article_id:
                try:
                    article_id = uuid.UUID(article_id)
                except ValueError:
                    article_id = None
            
            theory = await TheoryRepository.create(
                db=db,
                theory_name=theory_name,
                description=description,
                evidence_level=data.get('evidence_level'),
                category=data.get('category'),
                first_mentioned_in_article_id=article_id,
            )
            await db.commit()
        
        logger.info(f"Created theory: {theory.theory_name}")
        return (
            f"Theory created successfully!\n"
            f"Theory ID: {theory.id}\n"
            f"Name: {theory_name}\n"
            f"Category: {theory.category}\n"
            f"Evidence Level: {theory.evidence_level}"
        )
        
    except json.JSONDecodeError as e:
        return f"Error parsing theory data JSON: {str(e)}"
    except Exception as e:
        logger.error(f"Error creating theory: {e}")
        return f"Error creating theory: {str(e)}"


@tool
async def link_article_theory(article_id: str, theory_id: str, relevance_score: float = 0.8, context: str = "") -> str:
    """
    Link an article with an aging theory.
    
    Args:
        article_id: UUID of the article
        theory_id: UUID of the theory
        relevance_score: How relevant is the theory to the article (0-1), default 0.8
        context: Context/excerpt from article where theory is mentioned
        
    Returns:
        String confirming the link
    """
    try:
        # Convert to UUIDs
        try:
            article_uuid = uuid.UUID(article_id)
            theory_uuid = uuid.UUID(theory_id)
        except ValueError as e:
            return f"Error: Invalid UUID format - {str(e)}"
        
        async with get_db() as db:
            # Create link
            link = await ArticleTheoryRepository.create_link(
                db=db,
                article_id=article_uuid,
                theory_id=theory_uuid,
                relevance_score=relevance_score,
                extracted_context=context[:1000] if context else None,  # Limit context length
            )
            await db.commit()
        
        logger.info(f"Linked article {article_id} with theory {theory_id}")
        return (
            f"Successfully linked article with theory!\n"
            f"Link ID: {link.id}\n"
            f"Relevance Score: {relevance_score}\n"
            f"The theory mention count has been incremented."
        )
        
    except Exception as e:
        logger.error(f"Error linking article and theory: {e}")
        return f"Error creating link: {str(e)}"


# Export tools
database_tools = [
    check_article_exists,
    save_article,
    find_similar_theory,
    create_theory,
    link_article_theory,
]

