import json
from typing import List, Dict
from langchain_core.tools import tool
from openai import OpenAI
from loguru import logger
from sentence_transformers import SentenceTransformer

from config import config
from db.database import get_db
from db.repository import TheoryRepository


# Initialize embedding model (lazy loading)
_embedding_model = None

def get_embedding_model():
    """Lazy load embedding model"""
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {config.embedding_model}")
        _embedding_model = SentenceTransformer(config.embedding_model)
    return _embedding_model


@tool
async def extract_aging_theories(text: str, article_title: str = "") -> str:
    """
    Extract aging theories from article text using AI.
    This tool identifies specific theories or hypotheses about aging mechanisms mentioned in the text.
    It also checks against existing theories in the database to avoid duplicates.
    
    DEPRECATED: This tool uses embedding-based semantic matching.
    For production use, prefer TheoryClassificationService which uses LLM for better accuracy.
    
    Args:
        text: Full text or abstract of the article
        article_title: Title of the article (optional, for context)
        
    Returns:
        JSON string with extracted theories
    """
    try:
        logger.info(f"Extracting theories from: {article_title[:50]}...")
        
        # Get existing theories for context
        async with get_db() as db:
            existing_theories = await TheoryRepository.list_theories(db, limit=100)
        
        existing_theories_text = "\n".join([
            f"- {t.theory_name}: {t.description[:100]}..."
            for t in existing_theories[:20]  # Limit to avoid token overflow
        ])
        
        # Prepare prompt for LLM
        prompt = f"""You are an expert in aging research. Extract specific aging theories, hypotheses, or mechanisms mentioned in the following article text.

Article Title: {article_title}

Existing theories in database (reuse these if applicable):
{existing_theories_text}

Instructions:
1. Identify specific aging theories, mechanisms, or hypotheses discussed
2. For each theory, provide:
   - theory_name: Clear, concise name (e.g., "Free Radical Theory", "Telomere Shortening")
   - description: Brief description of the theory/mechanism
   - evidence_level: "weak", "moderate", or "strong" based on evidence presented
   - category: One of "nutritional", "genetic", "cellular", "molecular", "systemic", "evolutionary", "other"
3. If a theory matches an existing one, use the EXACT same name
4. Only extract theories that are EXPLICITLY discussed (not just mentioned in passing)
5. Return results as JSON array

Article Text:
{text[:5000]}

Return ONLY a JSON array of extracted theories. Example format:
[
  {{
    "theory_name": "Mitochondrial Dysfunction Theory",
    "description": "Age-related decline in mitochondrial function leads to increased ROS production and cellular damage",
    "evidence_level": "strong",
    "category": "cellular"
  }}
]

If no clear theories are found, return an empty array: []
"""
        
        # Call LLM
        client = OpenAI(
            base_url="https://api.studio.nebius.com/v1/",
            api_key=config.nebius_api_key
        )
        
        response = client.chat.completions.create(
            model=config.theory_llm_model,
            max_tokens=1024,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        logger.debug(f"Raw LLM response: {result_text[:200]}...")
        
        # Parse response
        try:
            # Try to parse as object first (might be wrapped)
            result_obj = json.loads(result_text)
            if isinstance(result_obj, dict):
                # Extract theories array from dict
                theories = result_obj.get('theories', result_obj.get('aging_theories', []))
                if not isinstance(theories, list):
                    theories = []
            else:
                theories = result_obj
        except json.JSONDecodeError:
            theories = []
        
        if not theories:
            logger.info("No theories extracted from text")
            return json.dumps({
                "status": "success",
                "theories_found": 0,
                "theories": []
            })
        
        logger.info(f"Extracted {len(theories)} theories from text")
        
        # Semantic matching with existing theories
        model = get_embedding_model()
        matched_theories = []
        
        for theory in theories:
            theory_name = theory.get('theory_name', '')
            theory_desc = theory.get('description', '')
            
            if not theory_name:
                continue
            
            # Check for exact name match first
            matched = False
            for existing in existing_theories:
                if existing.theory_name.lower() == theory_name.lower():
                    theory['matched_theory_id'] = str(existing.id)
                    theory['matched_theory_name'] = existing.theory_name
                    matched = True
                    break
            
            if not matched and len(existing_theories) > 0:
                # Semantic similarity check
                query_embedding = model.encode(f"{theory_name} {theory_desc}")
                
                best_match = None
                best_score = 0
                
                for existing in existing_theories[:50]:  # Check top 50
                    existing_text = f"{existing.theory_name} {existing.description}"
                    existing_embedding = model.encode(existing_text)
                    
                    # Cosine similarity
                    from numpy import dot
                    from numpy.linalg import norm
                    similarity = dot(query_embedding, existing_embedding) / (norm(query_embedding) * norm(existing_embedding))
                    
                    if similarity > best_score:
                        best_score = similarity
                        best_match = existing
                
                # If similarity above threshold, consider it a match
                if best_score >= config.theory_similarity_threshold:
                    theory['matched_theory_id'] = str(best_match.id)
                    theory['matched_theory_name'] = best_match.theory_name
                    theory['similarity_score'] = float(best_score)
                    logger.info(f"Theory '{theory_name}' matched with '{best_match.theory_name}' (score: {best_score:.3f})")
            
            matched_theories.append(theory)
        
        return json.dumps({
            "status": "success",
            "theories_found": len(matched_theories),
            "theories": matched_theories
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Theory extraction failed: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "theories_found": 0,
            "theories": []
        })


# Export tools
theory_extraction_tools = [extract_aging_theories]
