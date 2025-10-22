import json
from typing import Optional
from openai import OpenAI
from loguru import logger

from config import config, MODEL_PRICING
from prompt_service import PromptService
from prompt_schemas import AgingTheoryAnalysisRequest, AgingTheoryAnalysisResponse
from cost_tracker import CostInfo


class AnalysisService:
    """
    Service for analyzing aging research papers using AI
    """
    
    def __init__(self):
        self.prompt_service = PromptService(prompts_dir="prompts")
        self.client = OpenAI(
            base_url="https://api.studio.nebius.com/v1/",
            api_key=config.nebius_api_key
        )
    
    async def analyze_paper(
        self,
        article_title: str,
        full_text: str,
        model: Optional[str] = None
    ) -> tuple[AgingTheoryAnalysisResponse, CostInfo]:
        """
        Analyze a paper using the 9-question framework
        
        Args:
            article_title: Title of the article
            full_text: Full text of the article (from PDF)
            model: Model to use for analysis
            
        Returns:
            Tuple of (AgingTheoryAnalysisResponse, CostInfo)
        """
        # Create the request schema
        request = AgingTheoryAnalysisRequest(
            article_title=article_title,
            abstract_text=full_text[:8000]  # Limit text size to avoid token limits
        )
        
        # Compile the prompt
        logger.info(f"📋 Compiling analysis prompt for: {article_title[:50]}...")
        compiled_prompt = self.prompt_service.compile_prompt(request)
        logger.info(f"✓ Prompt compiled ({len(compiled_prompt)} chars, ~{len(compiled_prompt)//4} tokens)")
        
        # Make API call with response_format for structured output
        selected_model = model or config.analysis_llm_model
        logger.info(f"🤖 Calling AI model ({selected_model}) for 9-question analysis...")
        
        response = self.client.chat.completions.create(
            model=selected_model,
            max_tokens=2048,
            temperature=0.6,
            top_p=0.9,
            extra_body={
                "top_k": 50
            },
            messages=[
                {
                    "role": "user",
                    "content": compiled_prompt
                }
            ],
            response_format={"type": "json_object"}
        )
        
        logger.info(f"✓ AI response received")
        
        # Calculate costs based on token usage
        usage = response.usage
        cost_info = self._calculate_cost(
            model=selected_model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens
        )
        logger.info(f"💰 Analysis cost: ${cost_info.total_cost_usd:.6f} ({usage.prompt_tokens} in + {usage.completion_tokens} out)")
        
        # Extract and parse the response
        content = response.choices[0].message.content
        logger.debug(f"Raw analysis response: {content[:200]}...")
        
        # Parse JSON response into structured model
        logger.info(f"📊 Parsing analysis results...")
        try:
            response_data = json.loads(content)
            analysis_result = AgingTheoryAnalysisResponse(**response_data)
            logger.info(f"✓ Analysis completed successfully for: {article_title[:50]}...")
            return analysis_result, cost_info
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse analysis response: {e}")
            raise
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> CostInfo:
        """
        Calculate the cost of an API call based on token usage
        
        Args:
            model: Model name
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            
        Returns:
            CostInfo object with detailed cost breakdown
        """
        pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
        
        # Calculate costs (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        cost_info = CostInfo(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            total_cost_usd=total_cost,
            model=model
        )
        
        logger.info(f"💰 {cost_info}")
        return cost_info
