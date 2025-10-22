import csv
import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from loguru import logger

from config import config, MODEL_PRICING
from prompt_service import PromptService
from prompt_schemas import AgingTheoryAnalysisRequest, AgingTheoryAnalysisResponse
from cost_tracker import CostInfo, CostTracker


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> CostInfo:
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


async def analyze_aging_theory(
    article_title: str,
    abstract_text: str,
    model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
) -> tuple[AgingTheoryAnalysisResponse, CostInfo]:
    """
    Analyze an aging theory paper and answer 9 key questions
    
    Args:
        article_title: The title of the article
        abstract_text: The abstract text of the article
        model: Model to use for analysis
        
    Returns:
        Tuple of (AgingTheoryAnalysisResponse, CostInfo)
    """
    # Initialize services
    prompt_service = PromptService(prompts_dir="prompts")
    
    # Create the request schema
    request = AgingTheoryAnalysisRequest(
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
        max_tokens=1024,  # Increased for detailed analysis
        temperature=0.3,  # Lower temperature for more consistent answers
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
        analysis_result = AgingTheoryAnalysisResponse(**response_data)
        logger.info(f"Analysis completed for: {article_title[:50]}...")
        return analysis_result, cost_info
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse response: {e}")
        raise


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


def save_analysis_to_csv(
    results: list[dict],
    output_file: str | Path = "aging_theory_analysis_results.csv"
) -> None:
    """
    Save analysis results to a CSV file
    
    Args:
        results: List of analysis results with metadata
        output_file: Path to the output CSV file
    """
    if not results:
        logger.warning("No results to save")
        return
    
    output_path = Path(output_file)
    
    # Define CSV columns
    fieldnames = [
        "theory_id",
        "paper_name",
        "Q1: Aging biomarker?",
        "Q1: Explanation",
        "Q2: Molecular mechanism?",
        "Q2: Explanation",
        "Q3: Longevity intervention?",
        "Q3: Explanation",
        "Q4: Aging irreversible?",
        "Q4: Explanation",
        "Q5: Species lifespan biomarker?",
        "Q5: Explanation",
        "Q6: Naked mole rat explanation?",
        "Q6: Explanation",
        "Q7: Bird longevity explanation?",
        "Q7: Explanation",
        "Q8: Size-lifespan explanation?",
        "Q8: Explanation",
        "Q9: Calorie restriction explanation?",
        "Q9: Explanation",
        "API cost (USD)",
        "Input tokens",
        "Output tokens",
        "Total tokens"
    ]
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, result in enumerate(results, 1):
                analysis = result["analysis"]
                cost = result["cost"]
                
                row = {
                    "theory_id": i,
                    "paper_name": result["title"],
                    "Q1: Aging biomarker?": analysis.q1_biomarker,
                    "Q1: Explanation": analysis.q1_explanation,
                    "Q2: Molecular mechanism?": analysis.q2_molecular_mechanism,
                    "Q2: Explanation": analysis.q2_explanation,
                    "Q3: Longevity intervention?": analysis.q3_longevity_intervention,
                    "Q3: Explanation": analysis.q3_explanation,
                    "Q4: Aging irreversible?": analysis.q4_aging_irreversible,
                    "Q4: Explanation": analysis.q4_explanation,
                    "Q5: Species lifespan biomarker?": analysis.q5_species_lifespan_biomarker,
                    "Q5: Explanation": analysis.q5_explanation,
                    "Q6: Naked mole rat explanation?": analysis.q6_naked_mole_rat,
                    "Q6: Explanation": analysis.q6_explanation,
                    "Q7: Bird longevity explanation?": analysis.q7_bird_longevity,
                    "Q7: Explanation": analysis.q7_explanation,
                    "Q8: Size-lifespan explanation?": analysis.q8_size_lifespan,
                    "Q8: Explanation": analysis.q8_explanation,
                    "Q9: Calorie restriction explanation?": analysis.q9_calorie_restriction,
                    "Q9: Explanation": analysis.q9_explanation,
                    "API cost (USD)": f"${cost.total_cost_usd:.6f}",
                    "Input tokens": cost.input_tokens,
                    "Output tokens": cost.output_tokens,
                    "Total tokens": cost.total_tokens
                }
                
                writer.writerow(row)
        
        logger.info(f"✓ Results saved to: {output_path.absolute()}")
        logger.info(f"  Total rows: {len(results)}")
        
    except Exception as e:
        logger.error(f"Failed to save CSV file: {e}")
        raise


async def batch_analyze_theories():
    """Batch analyze aging theories from folder and save to CSV"""
    # Load articles from the examples/abstracts folder
    articles = load_articles_from_folder("examples/abstracts")
    
    if not articles:
        logger.error("No articles found to analyze")
        return
    
    # Initialize cost tracker
    tracker = CostTracker()
    
    logger.info("=" * 80)
    logger.info("Starting batch analysis of aging theories...")
    logger.info(f"Found {len(articles)} articles to analyze")
    logger.info("=" * 80)
    
    # Process each article
    results = []
    for i, article in enumerate(articles, 1):
        logger.info(f"\n[{i}/{len(articles)}] Analyzing: {article['title']}")
        logger.info("-" * 80)
        
        try:
            analysis, cost_info = await analyze_aging_theory(
                article["title"],
                article["abstract"]
            )
            
            # Add cost to tracker
            tracker.add_call(cost_info)
            
            # Store result
            results.append({
                "title": article["title"],
                "analysis": analysis,
                "cost": cost_info
            })
            
            # Log summary of answers
            yes_count = sum([
                analysis.q1_biomarker == "Yes",
                analysis.q2_molecular_mechanism == "Yes",
                analysis.q3_longevity_intervention == "Yes",
                analysis.q4_aging_irreversible == "Yes",
                analysis.q5_species_lifespan_biomarker == "Yes",
                analysis.q6_naked_mole_rat == "Yes",
                analysis.q7_bird_longevity == "Yes",
                analysis.q8_size_lifespan == "Yes",
                analysis.q9_calorie_restriction == "Yes",
            ])
            
            logger.info(f"✓ Analysis complete: {yes_count}/9 questions answered 'Yes'")
            logger.info(f"  Cost: ${cost_info.total_cost_usd:.6f}")
            
        except Exception as e:
            logger.error(f"✗ Failed to analyze article: {e}")
        
        logger.info("-" * 80)
    
    # Save results to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"aging_theory_analysis_{timestamp}.csv"
    save_analysis_to_csv(results, output_file)
    
    # Print cost summary
    logger.info("\n")
    tracker.print_summary()
    
    # Print analysis summary
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("ANALYSIS SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total theories analyzed: {len(results)}")
    logger.info(f"Results saved to: {output_file}")
    logger.info("=" * 80)


async def main():
    """Main entry point"""
    await batch_analyze_theories()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

