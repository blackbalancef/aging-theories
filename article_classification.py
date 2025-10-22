import os
import json
from pathlib import Path
from openai import OpenAI
from loguru import logger

from config import config, MODEL_PRICING
from prompt_service import PromptService
from prompt_schemas import ArticleClassificationRequest, ArticleClassificationResponse
from cost_tracker import CostInfo, CostTracker


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> CostInfo:
    """
    Calculate the cost of an API call based on token usage
    
    Args:
        model: Model name (e.g., "meta-llama/Meta-Llama-3.1-8B-Instruct")
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


async def classify_article(
    article_title: str, 
    abstract_text: str,
    model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
) -> tuple[ArticleClassificationResponse, CostInfo]:
    """
    Classify an article as aging-related or not using structured output
    
    Args:
        article_title: The title of the article
        abstract_text: The abstract text of the article
        model: Model to use for classification
        
    Returns:
        Tuple of (ArticleClassificationResponse, CostInfo)
    """
    # Initialize services
    prompt_service = PromptService(prompts_dir="prompts")
    
    # Create the request schema
    request = ArticleClassificationRequest(
        article_title=article_title,
        abstract_text=abstract_text
    )
    
    # Compile the prompt
    compiled_prompt = prompt_service.compile_prompt(request)
    logger.debug(f"Compiled prompt with {len(compiled_prompt)} characters")
    
    # Initialize OpenAI client for Nebius
    client = OpenAI(
        base_url="https://api.studio.nebius.com/v1/",
        api_key=config.nebius_api_key
    )
    
    # Make API call with response_format for structured output
    response = client.chat.completions.create(
        model=model,
        max_tokens=512,
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
    
    # Calculate costs based on token usage
    usage = response.usage
    cost_info = calculate_cost(
        model=model,
        input_tokens=usage.prompt_tokens,
        output_tokens=usage.completion_tokens
    )
    
    # Extract and parse the response
    content = response.choices[0].message.content
    logger.debug(f"Raw response: {content}")
    
    # Parse JSON response into structured model
    try:
        response_data = json.loads(content)
        classification_result = ArticleClassificationResponse(**response_data)
        logger.info(f"Classification result: {classification_result.is_aging_related} (confidence: {classification_result.confidence})")
        return classification_result, cost_info
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse response: {e}")
        raise


async def main():
    """Example usage of article classification"""
    # Example: Single article classification
    title = "The hyperfunction theory: an emerging paradigm for the biology of aging"
    abstract = """
    Aging is characterized by a progressive decline in physiological functions and an increased 
    susceptibility to age-related diseases. The hyperfunction theory proposes that aging results 
    from the continuation of developmental growth programs that become harmful in adulthood. 
    This theory suggests that interventions targeting these hyperfunctional pathways could 
    potentially slow aging and extend healthspan.
    """
    
    result, cost_info = await classify_article(title, abstract)
    
    logger.info("=" * 80)
    logger.info(f"Article: {title}")
    logger.info(f"Is Aging Related: {result.is_aging_related}")
    logger.info(f"Confidence: {result.confidence}")
    logger.info(f"Explanation: {result.explanation}")
    logger.info("-" * 80)
    logger.info(f"Cost Breakdown:")
    logger.info(f"  Model: {cost_info.model}")
    logger.info(f"  Input tokens: {cost_info.input_tokens} (${cost_info.input_cost_usd:.6f})")
    logger.info(f"  Output tokens: {cost_info.output_tokens} (${cost_info.output_cost_usd:.6f})")
    logger.info(f"  Total tokens: {cost_info.total_tokens}")
    logger.info(f"  Total cost: ${cost_info.total_cost_usd:.6f}")
    logger.info("=" * 80)


def load_articles_from_folder(folder_path: str | Path = "examples/abstracts") -> list[dict[str, str]]:
    """
    Load articles from a folder where each file contains an abstract
    
    Args:
        folder_path: Path to the folder containing article files
        
    Returns:
        List of dictionaries with 'title' and 'abstract' keys
    """
    folder = Path(folder_path)
    
    if not folder.exists():
        logger.error(f"Folder not found: {folder}")
        return []
    
    articles = []
    
    # Find all .txt files in the folder
    for file_path in sorted(folder.glob("*.txt")):
        # Use filename (without extension) as title
        title = file_path.stem
        
        # Read abstract from file
        try:
            abstract = file_path.read_text(encoding="utf-8").strip()
            
            # Remove "Abstract" header if present at the beginning
            if abstract.lower().startswith("abstract"):
                lines = abstract.split("\n", 1)
                if len(lines) > 1:
                    abstract = lines[1].strip()
            
            articles.append({
                "title": title,
                "abstract": abstract
            })
            logger.debug(f"Loaded article: {title}")
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
    
    logger.info(f"Loaded {len(articles)} articles from {folder}")
    return articles


async def batch_classify_example():
    """Example of batch classification with cost tracking using real articles"""
    # Load articles from the examples/abstracts folder
    articles = load_articles_from_folder("examples/abstracts")
    
    if not articles:
        logger.error("No articles found to classify")
        return
    
    # Initialize cost tracker for batch processing
    tracker = CostTracker()
    
    logger.info("Starting batch classification...")
    logger.info("=" * 80)
    
    # Process each article
    results = []
    for i, article in enumerate(articles, 1):
        logger.info(f"\nProcessing article {i}/{len(articles)}:")
        logger.info(f"Title: {article['title']}")
        
        try:
            result, cost_info = await classify_article(article["title"], article["abstract"])
            
            # Add cost to tracker
            tracker.add_call(cost_info)
            
            # Store result
            results.append({
                "title": article["title"],
                "result": result,
                "cost": cost_info
            })
            
            logger.info(f"✓ Result: {result.is_aging_related.upper()} (confidence: {result.confidence})")
            logger.info(f"  Explanation: {result.explanation}")
            logger.info(f"  Cost: ${cost_info.total_cost_usd:.6f}")
            
        except Exception as e:
            logger.error(f"✗ Failed to classify article: {e}")
        
        logger.info("-" * 80)
    
    # Print cumulative cost summary
    tracker.print_summary()
    
    # Print summary of results
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("CLASSIFICATION RESULTS SUMMARY")
    logger.info("=" * 80)
    aging_related = sum(1 for r in results if r["result"].is_aging_related == "yes")
    not_aging = sum(1 for r in results if r["result"].is_aging_related == "no")
    logger.info(f"Total articles: {len(results)}")
    logger.info(f"Aging-related: {aging_related}")
    logger.info(f"Not aging-related: {not_aging}")
    logger.info("=" * 80)


if __name__ == "__main__":
    import asyncio
    # For single article example, use main()
    # For batch processing with real articles, use batch_classify_example()
    asyncio.run(batch_classify_example())