import asyncio
from typing import List, Dict, Any
from langchain_core.tools import tool
from loguru import logger

from crawlers.pubmed import PubmedCrawler
from crawlers.pmc import PmcCrawler
from config import config


@tool
async def search_pubmed(query: str, max_papers: int = 20) -> str:
    """
    Search PubMed database for research articles.
    
    Args:
        query: PubMed search query (e.g., "aging mechanisms[Title/Abstract]")
        max_papers: Maximum number of papers to retrieve (default: 20)
        
    Returns:
        Formatted string with article information (title, DOI, abstract, etc.)
    """
    try:
        logger.info(f"Searching PubMed: {query} (max: {max_papers})")
        
        # Run crawler in thread pool since it's synchronous
        def run_crawler():
            crawler = PubmedCrawler(
                email=config.ncbi_email or config.pubmed_email,
                api_key=config.ncbi_api_key or config.pubmed_api_key,
                max_papers=max_papers
            )
            
            # Override build_queries to use provided query
            original_build = crawler.build_queries
            crawler.build_queries = lambda: {"custom": query}
            
            df = crawler.run()
            return df.to_dict('records')
        
        # Execute in thread pool to not block async
        loop = asyncio.get_event_loop()
        records = await loop.run_in_executor(None, run_crawler)
        
        if not records:
            return f"No articles found in PubMed for query: {query}"
        
        # Format results
        preview_limit = min(len(records), max(1, min(max_papers, 5)))
        formatted_results = []
        for i, record in enumerate(records[:preview_limit], 1):
            title = record.get('paper_name', 'No title')
            doi_url = record.get('doi_url', 'No DOI')
            abstract = record.get('abstract', 'No abstract')[:300]
            year = record.get('paper_year', 'N/A')
            keywords = record.get('keywords', 'N/A')
            
            formatted_results.append(
                f"{i}. {title} ({year})\n"
                f"   DOI: {doi_url}\n"
                f"   Keywords: {keywords}\n"
                f"   Abstract: {abstract}...\n"
            )
        
        result_text = "\n".join(formatted_results)
        if len(records) > preview_limit:
            result_text += (
                f"\n...and {len(records) - preview_limit} more PubMed matches. "
                "Call save tools selectively to avoid token limits."
            )
        logger.info(f"Found {len(records)} articles in PubMed")
        
        return f"PubMed results for '{query}':\n\n{result_text}"
        
    except Exception as e:
        logger.error(f"PubMed search failed: {e}")
        return f"Error searching PubMed: {str(e)}"


@tool
async def search_pmc(query: str, max_papers: int = 20) -> str:
    """
    Search PubMed Central (PMC) database for full-text articles.
    
    Args:
        query: PMC search query (e.g., "cellular senescence[Title/Abstract]")
        max_papers: Maximum number of papers to retrieve (default: 20)
        
    Returns:
        Formatted string with article information (title, DOI, abstract, etc.)
    """
    try:
        logger.info(f"Searching PMC: {query} (max: {max_papers})")
        
        # Run crawler in thread pool since it's synchronous
        def run_crawler():
            crawler = PmcCrawler(
                email=config.pmc_email or config.ncbi_email,
                api_key=config.pmc_api_key or config.ncbi_api_key,
                max_papers=max_papers
            )
            
            # Override build_queries to use provided query
            original_build = crawler.build_queries
            crawler.build_queries = lambda: {"custom": query}
            
            # Get records directly without full run
            count, webenv, query_key = crawler.search_with_history(query)
            if count > 0:
                records = crawler.fetch_records(
                    min(count, max_papers),
                    webenv,
                    query_key
                )
                return records
            return []
        
        # Execute in thread pool to not block async
        loop = asyncio.get_event_loop()
        records = await loop.run_in_executor(None, run_crawler)
        
        if not records:
            return f"No articles found in PMC for query: {query}"
        
        # Format results
        preview_limit = min(len(records), max(1, min(max_papers, 5)))
        formatted_results = []
        for i, record in enumerate(records[:preview_limit], 1):
            title = record.get('paper_name', 'No title')
            doi_url = record.get('doi_url', 'No DOI')
            abstract = record.get('abstract', 'No abstract')
            if abstract and len(abstract) > 300:
                abstract = abstract[:300]
            year = record.get('paper_year', 'N/A')
            keywords = record.get('keywords', 'N/A')
            
            formatted_results.append(
                f"{i}. {title} ({year})\n"
                f"   DOI: {doi_url}\n"
                f"   Keywords: {keywords}\n"
                f"   Abstract: {abstract}...\n"
            )
        
        result_text = "\n".join(formatted_results)
        if len(records) > preview_limit:
            result_text += (
                f"\n...and {len(records) - preview_limit} more PMC matches. "
                "Request additional details only for the most relevant entries."
            )
        logger.info(f"Found {len(records)} articles in PMC")
        
        return f"PMC results for '{query}':\n\n{result_text}"
        
    except Exception as e:
        logger.error(f"PMC search failed: {e}")
        return f"Error searching PMC: {str(e)}"


# Export tools
crawler_tools = [search_pubmed, search_pmc]
