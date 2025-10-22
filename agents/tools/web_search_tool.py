from typing import Optional
from langchain_core.tools import tool
from ddgs import DDGS
from loguru import logger


@tool
async def search_articles_web(query: str, max_results: int = 10) -> str:
    """
    Search for scientific articles and research papers on the web.
    
    Args:
        query: Search query for articles (e.g., "aging theories 2024")
        max_results: Maximum number of results to return (default: 10)
        
    Returns:
        Formatted string with search results including titles, URLs, and snippets
    """
    try:
        logger.info(f"🔎 Web search for articles: '{query}' (max: {max_results})")
        
        with DDGS() as ddgs:
            # Use text search for general web results
            results = list(ddgs.text(
                query,
                max_results=max_results,
                region='wt-wt',  # Worldwide
                safesearch='moderate'
            ))
        
        if not results:
            return f"No results found for query: {query}"
        
        # Format results
        preview_limit = min(len(results), max(1, min(max_results, 5)))
        formatted_results = []
        for i, result in enumerate(results[:preview_limit], 1):
            title = result.get('title', 'No title')
            url = result.get('href', result.get('link', 'No URL'))
            snippet = result.get('body', result.get('snippet', 'No description'))
            
            formatted_results.append(
                f"{i}. {title}\n"
                f"   URL: {url}\n"
                f"   Description: {snippet[:200]}...\n"
            )
        
        result_text = "\n".join(formatted_results)
        if len(results) > preview_limit:
            result_text += (
                f"\n...and {len(results) - preview_limit} more web results. "
                "Open the most relevant URLs before saving."
            )
        logger.info(f"✓ Found {len(results)} web results for '{query}'")
        
        return f"Search results for '{query}':\n\n{result_text}"
        
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"Error performing web search: {str(e)}"


@tool
async def search_article_reviews(doi: str, title: str) -> str:
    """
    Search for reviews, citations, and criticisms of a specific article.
    
    Args:
        doi: DOI of the article
        title: Title of the article
        
    Returns:
        Formatted string with information about reviews and citations
    """
    try:
        logger.info(f"Searching for reviews of article: {title}")
        
        # Create targeted search queries
        queries = [
            f'"{title}" review OR critique OR criticism',
            f'"{title}" citation OR cited',
            f'{doi} review OR analysis',
        ]
        
        all_results = []
        
        with DDGS() as ddgs:
            for query in queries:
                try:
                    results = list(ddgs.text(
                        query,
                        max_results=5,
                        region='wt-wt',
                        safesearch='moderate'
                    ))
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"Query failed: {query} - {e}")
                    continue
        
        if not all_results:
            return f"No reviews or citations found for article: {title}"
        
        # Remove duplicates based on URL
        unique_results = {}
        for result in all_results:
            url = result.get('href', result.get('link', ''))
            if url and url not in unique_results:
                unique_results[url] = result
        
        # Format results
        preview_items = list(unique_results.items())[:5]
        formatted_results = []
        for i, (url, result) in enumerate(preview_items, 1):
            title_text = result.get('title', 'No title')
            snippet = result.get('body', result.get('snippet', 'No description'))
            
            formatted_results.append(
                f"{i}. {title_text}\n"
                f"   URL: {url}\n"
                f"   Context: {snippet[:200]}...\n"
            )
        
        result_text = "\n".join(formatted_results)
        if len(unique_results) > len(preview_items):
            result_text += (
                f"\n...and {len(unique_results) - len(preview_items)} more review/citation leads."
            )
        logger.info(f"Found {len(unique_results)} unique review/citation results")
        
        return (
            f"Reviews and citations for '{title}' (DOI: {doi}):\n\n"
            f"{result_text}\n\n"
            f"Note: Review these sources to assess the article's reception and impact."
        )
        
    except Exception as e:
        logger.error(f"Review search failed: {e}")
        return f"Error searching for reviews: {str(e)}"


# Export tools
web_search_tools = [search_articles_web, search_article_reviews]
