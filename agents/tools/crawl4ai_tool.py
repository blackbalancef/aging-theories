from typing import Optional
from langchain_core.tools import tool
from loguru import logger

# Crawl4AI is optional dependency
try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.extraction_strategy import LLMExtractionStrategy
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning("Crawl4AI not available. Install with: uv add crawl4ai")


@tool
async def crawl_webpage(url: str, extract_article: bool = True) -> str:
    """
    Crawl a webpage and extract its content, especially useful for scientific articles and research papers.
    
    Args:
        url: URL of the webpage to crawl
        extract_article: Whether to extract main article content (default: True)
        
    Returns:
        Extracted content from the webpage
    """
    if not CRAWL4AI_AVAILABLE:
        return "Error: Crawl4AI is not installed. Please install it with: uv add crawl4ai"
    
    try:
        logger.info(f"Crawling webpage: {url}")
        
        async with AsyncWebCrawler(verbose=False) as crawler:
            # Run crawl
            result = await crawler.arun(
                url=url,
                word_count_threshold=10,
                bypass_cache=True,
            )
            
            if not result.success:
                logger.error(f"Crawl failed for {url}: {result.error_message}")
                return f"Error: Failed to crawl {url} - {result.error_message}"
            
            # Extract content
            if extract_article and result.markdown:
                content = result.markdown
            else:
                content = result.cleaned_html or result.html
            
            # Limit content size
            if len(content) > 8000:
                logger.info(f"Truncating content from {len(content)} to 8000 chars")
                content = content[:8000] + "\n\n[Content truncated...]"
            
            logger.info(f"Successfully crawled {url} ({len(content)} chars)")
            
            return f"Content from {url}:\n\n{content}"
            
    except Exception as e:
        logger.error(f"Webpage crawling failed: {e}")
        return f"Error crawling webpage: {str(e)}"


@tool
async def crawl_research_portal(url: str, portal_type: str = "general") -> str:
    """
    Crawl a research portal or database page (like ResearchGate, Academia.edu, etc.)
    Optimized for extracting research paper information.
    
    Args:
        url: URL of the research portal page
        portal_type: Type of portal ("researchgate", "academia", "scholar", "general")
        
    Returns:
        Extracted research paper information
    """
    if not CRAWL4AI_AVAILABLE:
        return "Error: Crawl4AI is not installed. Please install it with: uv add crawl4ai"
    
    try:
        logger.info(f"Crawling research portal ({portal_type}): {url}")
        
        async with AsyncWebCrawler(
            verbose=False,
            headless=True,
        ) as crawler:
            # Run crawl
            result = await crawler.arun(
                url=url,
                word_count_threshold=10,
                bypass_cache=True,
            )
            
            if not result.success:
                logger.error(f"Crawl failed for {url}")
                return f"Error: Failed to crawl research portal {url}"
            
            # Try to extract structured content
            content = result.markdown or result.cleaned_html or result.html
            
            # Extract key information based on portal type
            if portal_type == "researchgate":
                # ResearchGate-specific extraction
                pass  # Add specific logic if needed
            elif portal_type == "academia":
                # Academia.edu-specific extraction
                pass
            
            # Limit content size
            if len(content) > 8000:
                content = content[:8000] + "\n\n[Content truncated...]"
            
            logger.info(f"Successfully crawled research portal ({len(content)} chars)")
            
            return f"Research portal content from {url}:\n\n{content}"
            
    except Exception as e:
        logger.error(f"Research portal crawling failed: {e}")
        return f"Error crawling research portal: {str(e)}"


# Export tools
crawl4ai_tools = [crawl_webpage, crawl_research_portal]

