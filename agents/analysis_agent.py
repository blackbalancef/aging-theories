import uuid
import json
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from loguru import logger

from config import config
from agents.tools.all_tools import analysis_tools
from services.analysis_service import AnalysisService
from db.database import get_db
from db.repository import ArticleRepository, AnalysisRepository


class AnalysisAgent:
    """
    Agent for deep analysis of research articles with review checking and theory extraction
    """
    
    def __init__(self):
        """Initialize Analysis Agent with LLM and tools"""
        # Initialize LLM
        # NOTE: max_tokens removed - Nebius API doesn't support max_completion_tokens parameter
        self.llm = ChatOpenAI(
            base_url="https://api.studio.nebius.com/v1/",
            api_key=config.nebius_api_key,
            model=config.analysis_llm_model,
            temperature=0.3,
        )
        
        # Initialize analysis service for 9-question framework
        self.analysis_service = AnalysisService()
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
        
        # Create agent using langgraph
        self.agent_executor = create_react_agent(
            model=self.llm,
            tools=analysis_tools,
        )
        
        logger.info(f"Analysis Agent initialized with model: {config.analysis_llm_model}")
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from template"""
        try:
            with open("prompts/analysis_agent_system.j2", "r") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Analysis system prompt not found, using default")
            return (
                "You are an Analysis Agent that deeply analyzes aging research articles. "
                "Parse PDFs, search for reviews, extract theories, and assess actuality."
            )
    
    
    async def analyze_article(
        self,
        article_id: uuid.UUID,
        doi: str,
        title: str,
        abstract: str,
        pdf_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of an article
        
        Args:
            article_id: Article UUID
            doi: Article DOI
            title: Article title
            abstract: Article abstract
            pdf_url: URL to PDF (optional)
            
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Starting analysis for article: {title[:50]}...")
        
        # Create analysis task
        task = (
            f"Analyze this research article:\n\n"
            f"Title: {title}\n"
            f"DOI: {doi}\n"
            f"Abstract: {abstract[:500]}...\n"
            f"PDF URL: {pdf_url or 'Not available'}\n"
            f"Article ID: {article_id}\n\n"
            f"Complete analysis workflow:\n"
            f"1. If PDF URL available, parse it to get full text\n"
            f"2. Search for reviews and citations of this article\n"
            f"3. Extract aging theories mentioned in the article\n"
            f"4. For each theory: find similar existing theories or create new ones\n"
            f"5. Link theories to this article\n"
            f"6. Assess actuality (0-1 score) based on reviews and citations\n"
            f"7. Determine controversy level (none/low/medium/high)\n"
            f"8. Provide comprehensive analysis report\n"
        )
        
        try:
            # Run agent for review search and theory extraction
            result = await self.agent_executor.ainvoke(
                {"messages": [
                    ("system", self.system_prompt),
                    ("user", task)
                ]},
            )
            
            messages = result.get("messages", [])
            final_answer = messages[-1].content if messages else ""
            intermediate_steps = []  # LangGraph doesn't expose intermediate steps the same way
            
            # Parse agent results
            analysis_data = self._parse_agent_results(intermediate_steps, final_answer)
            
            # Run 9-question analysis if we have full text
            full_text = analysis_data.get("full_text", "")
            if full_text:
                logger.info("Running 9-question framework analysis")
                nine_q_analysis, cost_info = await self.analysis_service.analyze_paper(
                    article_title=title,
                    full_text=full_text
                )
            else:
                # Use abstract if no full text
                logger.warning("No full text available, using abstract for analysis")
                nine_q_analysis, cost_info = await self.analysis_service.analyze_paper(
                    article_title=title,
                    full_text=abstract
                )
            
            # Save analysis to database
            async with get_db() as db:
                analysis_record = await AnalysisRepository.create(
                    db=db,
                    article_id=article_id,
                    analysis=nine_q_analysis,
                    full_text=full_text or abstract,
                    cost_info=cost_info,
                )
                
                # Update with agent analysis results
                analysis_record.review_summary = analysis_data.get("review_summary")
                analysis_record.citation_analysis = analysis_data.get("citation_analysis")
                analysis_record.actuality_score = analysis_data.get("actuality_score")
                analysis_record.controversy_level = analysis_data.get("controversy_level")
                
                await db.commit()
                
                logger.info(f"Saved analysis for article {article_id}")
            
            return {
                "status": "success",
                "article_id": str(article_id),
                "doi": doi,
                "analysis_report": final_answer,
                "actuality_score": analysis_data.get("actuality_score"),
                "controversy_level": analysis_data.get("controversy_level"),
                "theories_extracted": analysis_data.get("theories_count", 0),
                "cost": cost_info.total_cost_usd,
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return {
                "status": "error",
                "article_id": str(article_id),
                "error": str(e),
            }
    
    def _parse_agent_results(self, intermediate_steps: list, final_answer: str) -> Dict[str, Any]:
        """Parse results from agent execution"""
        data = {
            "full_text": None,
            "review_summary": None,
            "citation_analysis": {},
            "actuality_score": 0.5,  # Default medium
            "controversy_level": "low",  # Default low
            "theories_count": 0,
        }
        
        for step in intermediate_steps:
            action, observation = step
            tool_name = action.tool if hasattr(action, 'tool') else str(action)
            
            # Extract full text from PDF parsing
            if 'parse_pdf' in tool_name.lower():
                if 'Successfully extracted' in observation:
                    # Extract text from observation
                    lines = observation.split('\n')
                    text_start = False
                    text_lines = []
                    for line in lines:
                        if text_start:
                            text_lines.append(line)
                        elif line.strip().startswith('Successfully extracted text'):
                            text_start = True
                    
                    if text_lines:
                        data["full_text"] = '\n'.join(text_lines)
            
            # Extract review information
            elif 'search_article_reviews' in tool_name.lower():
                data["review_summary"] = observation[:1000]  # Limit length
                # Try to parse actuality hints from reviews
                if 'widely cited' in observation.lower() or 'recent' in observation.lower():
                    data["actuality_score"] = max(data["actuality_score"], 0.7)
                if 'contradicted' in observation.lower() or 'rebutted' in observation.lower():
                    data["actuality_score"] = min(data["actuality_score"], 0.4)
                    data["controversy_level"] = "high"
            
            # Count theories extracted
            elif 'extract_aging_theories' in tool_name.lower():
                try:
                    theories_data = json.loads(observation)
                    data["theories_count"] = theories_data.get("theories_found", 0)
                except:
                    pass
        
        # Try to extract scores from final answer
        if 'actuality' in final_answer.lower():
            # Look for score patterns like "actuality: 0.8" or "actuality score: 0.75"
            import re
            actuality_match = re.search(r'actuality[:\s]+([0-9.]+)', final_answer.lower())
            if actuality_match:
                try:
                    data["actuality_score"] = float(actuality_match.group(1))
                except:
                    pass
        
        if 'controversy' in final_answer.lower():
            for level in ['none', 'low', 'medium', 'high']:
                if level in final_answer.lower():
                    data["controversy_level"] = level
                    break
        
        return data
