import uuid
import asyncio
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from api.schemas import DiscoveryRequest, DiscoveryResponse
from services.discovery_service import DiscoveryService
from crawlers.pubmed import PubmedCrawler
from crawlers.pmc import PmcCrawler
from agents.discovery_agent import DiscoveryAgent
from config import config

router = APIRouter(prefix="/discover", tags=["discovery"])

# Store background task statuses (in production, use Redis or database)
discovery_tasks = {}


async def run_discovery_task(task_id: str, request: DiscoveryRequest):
    """
    Background task for running discovery
    """
    discovery_tasks[task_id] = {"status": "running", "progress": 0, "results": None}
    
    try:
        logger.info(f"Starting discovery task {task_id}")
        
        # Collect articles from specified sources
        all_articles = []
        
        if "pubmed" in request.sources:
            logger.info("Searching PubMed...")
            pubmed_crawler = PubmedCrawler(
                email=config.pubmed_email,
                api_key=config.pubmed_api_key,
                max_papers=request.max_papers,
            )
            
            # Use queries from request or default topics
            queries = request.queries or ["aging theory", "cellular senescence"]
            
            for query in queries:
                try:
                    count, webenv, query_key = pubmed_crawler.search_with_history(query)
                    if count > 0:
                        # fetch_records already calls parse_record internally
                        records = pubmed_crawler.fetch_records(
                            min(count, request.max_papers),
                            webenv,
                            query_key
                        )
                        # records are already parsed dictionaries
                        for parsed in records:
                            if parsed:  # Skip None records
                                # Convert year to int if it's a string
                                year = parsed.get("paper_year")
                                if year and isinstance(year, str):
                                    try:
                                        year = int(year)
                                    except (ValueError, TypeError):
                                        year = None
                                
                                all_articles.append({
                                    "doi": parsed.get("doi_url", f"pubmed_{parsed.get('paper_url', '')}"),
                                    "title": parsed.get("paper_name", ""),
                                    "abstract": parsed.get("abstract", ""),
                                    "source": "pubmed",
                                    "year": year,
                                    "journal": parsed.get("journal"),
                                    "keywords": parsed.get("keywords"),
                                    "full_text_url": parsed.get("paper_url"),
                                    "pdf_url": None,  # PubMed doesn't provide direct PDF links
                                })
                    
                    # Add small delay to respect API rate limits
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error searching PubMed with query '{query}': {e}")
        
        if "pmc" in request.sources:
            logger.info("Searching PMC...")
            pmc_crawler = PmcCrawler(
                email=config.pmc_email,
                api_key=config.pmc_api_key,
                max_papers=request.max_papers,
            )
            
            queries = request.queries or ["aging theory", "cellular senescence"]
            
            for query in queries:
                try:
                    count, webenv, query_key = pmc_crawler.search_with_history(query)
                    if count > 0:
                        # fetch_records already calls parse_record internally
                        records = pmc_crawler.fetch_records(
                            min(count, request.max_papers),
                            webenv,
                            query_key
                        )
                        # records are already parsed dictionaries
                        for parsed in records:
                            if parsed:  # Skip None records
                                # Try to construct PDF URL from PMC ID
                                pdf_url = None
                                paper_url = parsed.get("paper_url", "")
                                if paper_url and "PMC" in paper_url:
                                    # Extract PMC ID (handle trailing slash)
                                    pmc_id = paper_url.rstrip("/").split("/")[-1]
                                    if pmc_id.startswith("PMC"):
                                        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"
                                
                                # Convert year to int if it's a string
                                year = parsed.get("paper_year")
                                if year and isinstance(year, str):
                                    try:
                                        year = int(year)
                                    except (ValueError, TypeError):
                                        year = None
                                
                                all_articles.append({
                                    "doi": parsed.get("doi_url", f"pmc_{parsed.get('paper_url', '')}"),
                                    "title": parsed.get("paper_name", ""),
                                    "abstract": parsed.get("abstract", ""),
                                    "source": "pmc",
                                    "year": year,
                                    "journal": parsed.get("journal"),
                                    "keywords": parsed.get("keywords"),
                                    "full_text_url": parsed.get("paper_url"),
                                    "pdf_url": pdf_url,
                                })
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error searching PMC with query '{query}': {e}")
        
        # Process articles through discovery service
        logger.info(f"Processing {len(all_articles)} articles...")
        results = await DiscoveryService.process_articles_batch(all_articles)
        
        discovery_tasks[task_id] = {
            "status": "completed",
            "progress": 100,
            "results": results,
        }
        
        logger.info(f"Discovery task {task_id} completed: {results}")
        
    except Exception as e:
        logger.error(f"Discovery task {task_id} failed: {e}", exc_info=True)
        discovery_tasks[task_id] = {
            "status": "failed",
            "progress": 0,
            "error": str(e),
        }


@router.post("/start", response_model=DiscoveryResponse)
async def start_discovery(
    request: DiscoveryRequest,
    background_tasks: BackgroundTasks
):
    """
    Start discovery process for finding and classifying papers
    """
    task_id = str(uuid.uuid4())
    
    # Add background task
    background_tasks.add_task(run_discovery_task, task_id, request)
    
    logger.info(f"Started discovery task {task_id} with sources: {request.sources}")
    
    return DiscoveryResponse(
        task_id=task_id,
        status="started",
        message=f"Discovery task started with {len(request.sources)} sources"
    )


@router.get("/status/{task_id}")
async def get_discovery_status(task_id: str):
    """
    Get status of a discovery task
    """
    if task_id not in discovery_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task_id,
        **discovery_tasks[task_id]
    }


# New agent-based endpoints
class AgentDiscoveryRequest(BaseModel):
    """Request model for agent-based discovery"""
    topic: str = Field(..., description="Search topic or query")
    max_articles: int = Field(20, ge=1, le=100, description="Maximum articles to discover")
    sources: Optional[List[str]] = Field(
        None,
        description="Sources to search (pubmed, pmc, web, all). If None, agent decides."
    )


async def run_agent_discovery_task(task_id: str, request: AgentDiscoveryRequest):
    """Background task for running agent-based discovery"""
    discovery_tasks[task_id] = {"status": "running", "progress": 0, "results": None}
    
    try:
        logger.info(f"Starting agent discovery task {task_id} for topic: {request.topic}")
        
        # Initialize Discovery Agent
        agent = DiscoveryAgent()
        
        # Run discovery
        result = await agent.discover_articles(
            topic=request.topic,
            max_articles=request.max_articles,
            sources=request.sources,
            enqueue_for_analysis=True,
        )
        
        discovery_tasks[task_id] = {
            "status": "completed",
            "progress": 100,
            "results": result,
        }
        
        logger.info(f"Agent discovery task {task_id} completed")
        
    except Exception as e:
        logger.error(f"Agent discovery task {task_id} failed: {e}", exc_info=True)
        discovery_tasks[task_id] = {
            "status": "failed",
            "progress": 0,
            "error": str(e),
        }


@router.post("/agent/search", response_model=DiscoveryResponse)
async def agent_discovery(
    request: AgentDiscoveryRequest,
    background_tasks: BackgroundTasks
):
    """
    Start agent-based discovery process using Discovery Agent.
    
    The agent will intelligently search multiple sources, check for duplicates,
    classify articles, and save them to the database.
    
    - **topic**: Search topic (e.g., "mitochondrial dysfunction aging")
    - **max_articles**: Maximum number of articles to discover
    - **sources**: Optional list of sources to focus on
    """
    task_id = str(uuid.uuid4())
    
    # Add background task
    background_tasks.add_task(run_agent_discovery_task, task_id, request)
    
    logger.info(f"Started agent discovery task {task_id}")
    
    return DiscoveryResponse(
        task_id=task_id,
        status="started",
        message=f"Agent discovery started for topic: {request.topic}"
    )


@router.post("/agent/url")
async def agent_discovery_from_url(url: str):
    """
    Discover and save article from a specific URL using Discovery Agent.
    
    - **url**: URL of the article or research page
    """
    try:
        agent = DiscoveryAgent()
        result = await agent.discover_from_url(url)
        
        return result
        
    except Exception as e:
        logger.error(f"URL discovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

