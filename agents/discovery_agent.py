from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from loguru import logger

from config import config
from agents.tools.all_tools import discovery_tools
from task_queue.task_queue import TaskQueue


class DiscoveryAgent:
    """
    Agent for discovering research articles about aging from multiple sources
    """
    
    def __init__(self):
        """Initialize Discovery Agent with LLM and tools"""
        # Initialize LLM (using Nebius OpenAI-compatible API)
        # NOTE: max_tokens removed - Nebius API doesn't support max_completion_tokens parameter
        self.llm = ChatOpenAI(
            base_url="https://api.studio.nebius.com/v1/",
            api_key=config.nebius_api_key,
            model=config.discovery_llm_model,
            temperature=0.4,
        )
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
        
        # Create agent using langgraph
        # System prompt is prepended to messages, not a separate parameter
        self.agent_executor = create_react_agent(
            model=self.llm,
            tools=discovery_tools,
        )
        
        logger.info(f"Discovery Agent initialized with model: {config.discovery_llm_model}")
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from template"""
        try:
            with open("prompts/discovery_agent_system.j2", "r") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Discovery system prompt not found, using default")
            return (
                "You are a Discovery Agent that finds research articles about aging. "
                "Use available tools to search PubMed, PMC, and the web. "
                "Check for duplicates and save new articles to the database."
            )
    
    
    async def discover_articles(
        self,
        topic: str,
        max_articles: int = 20,
        sources: Optional[list[str]] = None,
        enqueue_for_analysis: bool = True,
    ) -> Dict[str, Any]:
        """
        Discover articles on a given topic
        
        Args:
            topic: Search topic or query
            max_articles: Maximum number of articles to discover
            sources: List of sources to search (pubmed, pmc, web, all)
            enqueue_for_analysis: Whether to enqueue articles for analysis
            
        Returns:
            Dictionary with discovery results
        """
        logger.info(f"Starting discovery for topic: {topic} (max: {max_articles})")
        
        # Prepare sources hint
        sources_hint = ""
        if sources:
            sources_hint = f"\nFocus on these sources: {', '.join(sources)}"
        
        # Create discovery task
        task = (
            f"Find research articles about: {topic}\n"
            f"Maximum articles to discover: {max_articles}{sources_hint}\n\n"
            f"Instructions:\n"
            f"1. Search multiple sources (PubMed, PMC, web)\n"
            f"2. Check each article for duplicates before saving\n"
            f"3. Extract complete metadata (DOI, title, abstract, PDF URL, etc.)\n"
            f"4. Save new articles to the database\n"
            f"5. Provide summary of findings\n"
        )
        
        try:
            logger.debug(f"Invoking agent with topic: {topic}")
            logger.debug(f"System prompt length: {len(self.system_prompt)} chars")
            logger.debug(f"Task length: {len(task)} chars")
            
            # Run agent with system prompt
            result = await self.agent_executor.ainvoke(
                {
                    "messages": [
                        ("system", self.system_prompt),
                        ("user", task)
                    ]
                },
                config={
                    "recursion_limit": 50,  # Limit recursion to prevent infinite loops
                }
            )
            
            # Parse results
            messages = result.get("messages", [])
            final_answer = messages[-1].content if messages else ""
            
            # Extract statistics from messages (LangGraph stores tool calls in messages)
            stats = self._extract_statistics_from_messages(messages)
            
            logger.info(f"Discovery completed: {stats}")
            
            return {
                "status": "success",
                "topic": topic,
                "final_answer": final_answer,
                "statistics": stats,
                "message_count": len(messages),
            }
            
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            logger.exception("Full error traceback:")
            return {
                "status": "error",
                "topic": topic,
                "error": str(e),
            }
    
    def _extract_statistics_from_messages(self, messages: list) -> Dict[str, int]:
        """Extract statistics from LangGraph messages"""
        stats = {
            "searches_performed": 0,
            "articles_found": 0,
            "articles_saved": 0,
            "duplicates_skipped": 0,
        }
        
        for msg in messages:
            # Check for tool calls in AI messages
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get('name', '') if isinstance(tool_call, dict) else getattr(tool_call, 'name', '')
                    
                    # Count searches (check for None)
                    if tool_name and 'search' in tool_name.lower():
                        stats["searches_performed"] += 1
            
            # Check for tool responses
            if hasattr(msg, 'name') and msg.name:
                tool_name = msg.name
                content = str(msg.content) if hasattr(msg, 'content') else ""
                
                # Count saves (check for None)
                if tool_name and 'save_article' in tool_name.lower():
                    if 'successfully' in content.lower():
                        stats["articles_saved"] += 1
                    elif 'already exists' in content.lower() or 'duplicate' in content.lower():
                        stats["duplicates_skipped"] += 1
        
        return stats
    
    async def discover_from_url(self, url: str) -> Dict[str, Any]:
        """
        Discover article from a specific URL
        
        Args:
            url: URL of the article or research page
            
        Returns:
            Dictionary with discovery results
        """
        logger.info(f"Discovering article from URL: {url}")
        
        task = (
            f"Extract and save the research article from this URL: {url}\n\n"
            f"Instructions:\n"
            f"1. Use crawl_webpage to extract content\n"
            f"2. Identify article metadata (DOI, title, abstract)\n"
            f"3. Check for duplicates\n"
            f"4. Save to database if new\n"
        )
        
        try:
            result = await self.agent_executor.ainvoke({
                "messages": [
                    ("system", self.system_prompt),
                    ("user", task)
                ]
            })
            
            messages = result.get("messages", [])
            final_answer = messages[-1].content if messages else ""
            
            return {
                "status": "success",
                "url": url,
                "result": final_answer,
            }
            
        except Exception as e:
            logger.error(f"URL discovery failed: {e}")
            return {
                "status": "error",
                "url": url,
                "error": str(e),
            }
