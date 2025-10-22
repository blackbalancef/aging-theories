import uuid
import json
from typing import List, Dict, Tuple, Optional
from openai import OpenAI
from loguru import logger
from jinja2 import Template

from config import config
from db.database import get_db
from db.repository import TheoryRepository, ArticleTheoryRepository


class TheoryClassificationService:
    """
    Service for extracting aging theories from articles and classifying them using LLM-based matching
    """
    
    def __init__(self):
        """Initialize the classification service"""
        self.llm_client = OpenAI(
            base_url="https://api.studio.nebius.com/v1/",
            api_key=config.nebius_api_key
        )
        self._load_prompt_template()
    
    def _load_prompt_template(self):
        """Load theory extraction prompt template"""
        try:
            with open("prompts/theory_extraction.j2", "r") as f:
                self.prompt_template = Template(f.read())
            logger.info("Loaded theory extraction prompt template")
        except FileNotFoundError:
            logger.warning("Theory extraction template not found, using default")
            self.prompt_template = None
    
    async def extract_theories_from_text(
        self, 
        article_text: str, 
        article_title: str = ""
    ) -> List[Dict]:
        """
        Extract aging theories from article text using LLM
        
        Args:
            article_text: Full text or abstract of the article
            article_title: Title of the article
            
        Returns:
            List of extracted theories with their properties
        """
        logger.info(f"Extracting theories from: {article_title[:50]}...")
        
        # Get existing theories from database
        async with get_db() as db:
            existing_theories = await TheoryRepository.list_theories(db, limit=100)
        
        # Prepare existing theories list for prompt
        existing_theories_list = "\n".join([
            f"- {t.theory_name}: {t.description[:150]}"
            for t in existing_theories[:30]  # Limit to avoid token overflow
        ])
        
        # Prepare prompt using template or default
        if self.prompt_template:
            prompt = self.prompt_template.render(
                existing_theories=existing_theories_list or "No existing theories yet",
                article_title=article_title,
                article_text=article_text[:6000]  # Limit text length
            )
        else:
            prompt = self._create_default_prompt(
                existing_theories_list, 
                article_title, 
                article_text[:6000]
            )
        
        try:
            # Call LLM to extract theories
            response = self.llm_client.chat.completions.create(
                model=config.theory_llm_model,
                max_tokens=2048,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            logger.debug(f"Raw LLM response: {result_text[:300]}...")
            
            # Parse JSON response
            result_obj = json.loads(result_text)
            
            # Extract theories array from various possible formats
            theories = []
            if isinstance(result_obj, list):
                theories = result_obj
            elif isinstance(result_obj, dict):
                theories = (
                    result_obj.get('theories') or 
                    result_obj.get('aging_theories') or 
                    result_obj.get('extracted_theories') or
                    []
                )
            
            logger.info(f"Extracted {len(theories)} theories from LLM")
            return theories
            
        except Exception as e:
            logger.error(f"Failed to extract theories: {e}", exc_info=True)
            return []
    
    def _create_default_prompt(self, existing_theories: str, title: str, text: str) -> str:
        """Create default extraction prompt if template not available"""
        return f"""Extract aging theories from this research article.

EXISTING THEORIES (prefer using these names if applicable):
{existing_theories}

ARTICLE:
Title: {title}

Content:
{text}

INSTRUCTIONS:
1. Identify specific aging theories, hypotheses, or mechanisms discussed
2. For each theory provide: theory_name, description, evidence_level (weak/moderate/strong), category
3. Categories: nutritional, genetic, cellular, molecular, systemic, evolutionary, other
4. If matches existing theory, use EXACT name
5. Only extract theories discussed with substantive detail
6. Return as JSON array

Return format:
{{
  "theories": [
    {{
      "theory_name": "Theory Name",
      "description": "Brief description",
      "evidence_level": "moderate",
      "category": "cellular"
    }}
  ]
}}
"""
    
    async def classify_and_link_theories(
        self,
        article_id: uuid.UUID,
        extracted_theories: List[Dict]
    ) -> Dict:
        """
        Classify extracted theories against existing ones and create links
        
        Args:
            article_id: UUID of the article
            extracted_theories: List of theories extracted from the article
            
        Returns:
            Dictionary with classification results
        """
        logger.info(f"Classifying {len(extracted_theories)} theories for article {article_id}")
        
        if not extracted_theories:
            return {
                "linked_count": 0,
                "new_theories_count": 0,
                "theory_links": []
            }
        
        # Get existing theories
        async with get_db() as db:
            existing_theories = await TheoryRepository.list_theories(db, limit=200)
        
        linked_count = 0
        new_theories_count = 0
        theory_links = []
        
        async with get_db() as db:
            for extracted in extracted_theories:
                theory_name = extracted.get('theory_name', '').strip()
                description = extracted.get('description', '').strip()
                evidence_level = extracted.get('evidence_level', 'moderate')
                category = extracted.get('category', 'other')
                
                if not theory_name or not description:
                    logger.warning(f"Skipping incomplete theory: {extracted}")
                    continue
                
                # Step 1: Try exact name match
                matched_theory = None
                for existing in existing_theories:
                    if existing.theory_name.lower() == theory_name.lower():
                        matched_theory = existing
                        logger.info(f"✓ Exact match found: '{theory_name}' -> '{existing.theory_name}'")
                        break
                
                # Step 2: If no exact match, use LLM for semantic matching
                if not matched_theory and len(existing_theories) > 0:
                    matched_theory, confidence = await self._find_similar_theory_with_llm(
                        theory_name,
                        description,
                        existing_theories,
                        category
                    )
                    
                    if matched_theory:
                        logger.info(
                            f"✓ LLM match: '{theory_name}' -> '{matched_theory.theory_name}' "
                            f"(confidence: {confidence})"
                        )
                
                # Step 3: Create new theory if no match found
                if not matched_theory:
                    logger.info(f"➕ Creating new theory: '{theory_name}'")
                    matched_theory = await TheoryRepository.create(
                        db=db,
                        theory_name=theory_name,
                        description=description,
                        evidence_level=evidence_level,
                        category=category,
                        first_mentioned_in_article_id=article_id
                    )
                    new_theories_count += 1
                    
                    # Add to existing list for subsequent matches
                    existing_theories.append(matched_theory)
                
                # Step 4: Create link between article and theory
                relevance_score = self._calculate_relevance_score(evidence_level)
                extracted_context = description[:500]  # Use description as context
                
                await ArticleTheoryRepository.create_link(
                    db=db,
                    article_id=article_id,
                    theory_id=matched_theory.id,
                    relevance_score=relevance_score,
                    extracted_context=extracted_context
                )
                
                linked_count += 1
                theory_links.append({
                    "theory_id": str(matched_theory.id),
                    "theory_name": matched_theory.theory_name,
                    "is_new": (matched_theory.id not in [t.id for t in existing_theories[:-1]]),
                    "relevance_score": relevance_score
                })
            
            await db.commit()
        
        logger.info(
            f"✅ Classification complete: {linked_count} links created, "
            f"{new_theories_count} new theories"
        )
        
        return {
            "linked_count": linked_count,
            "new_theories_count": new_theories_count,
            "theory_links": theory_links
        }
    
    async def _find_similar_theory_with_llm(
        self,
        theory_name: str,
        description: str,
        existing_theories: List,
        category: str
    ) -> Tuple[Optional[any], str]:
        """
        Find similar theory using LLM to determine conceptual similarity
        
        Args:
            theory_name: Name of the theory to match
            description: Description of the theory
            existing_theories: List of existing theories
            category: Category of the extracted theory
            
        Returns:
            Tuple of (matched_theory, confidence_level) or (None, "none")
        """
        if not existing_theories:
            return None, "none"
        
        # Filter theories by same category first to reduce token usage
        same_category_theories = [
            t for t in existing_theories 
            if t.category == category
        ]
        
        # If no theories in same category, use top 20 most mentioned theories
        theories_to_check = same_category_theories[:30] if same_category_theories else existing_theories[:20]
        
        if not theories_to_check:
            return None, "none"
        
        # Prepare theories list for LLM
        theories_list = "\n".join([
            f"{i+1}. {t.theory_name}\n   Description: {t.description[:200]}\n   Category: {t.category}\n   Mentions: {t.mention_count}"
            for i, t in enumerate(theories_to_check)
        ])
        
        # Create prompt for LLM
        prompt = f"""You are an expert in aging research. Determine if the extracted theory matches any existing theory in our database.

EXTRACTED THEORY:
Name: {theory_name}
Description: {description}
Category: {category}

EXISTING THEORIES IN DATABASE:
{theories_list}

TASK:
Analyze if the extracted theory is conceptually the same as any existing theory, considering:
- Core mechanism described
- Biological processes involved
- Scientific concepts referenced
- Different naming conventions (e.g., "Free Radical Theory" = "Oxidative Stress Theory")

Return JSON with:
- "match": true/false (is there a matching theory?)
- "theory_number": number from list (1-based) if match found, null otherwise
- "confidence": "high"/"medium"/"low" - how confident are you in the match?
- "reasoning": brief explanation of why it matches or doesn't match

Example output:
{{
  "match": true,
  "theory_number": 3,
  "confidence": "high",
  "reasoning": "Both theories describe the same mechanism of ROS damage from mitochondria, just using different terminology"
}}

Or if no match:
{{
  "match": false,
  "theory_number": null,
  "confidence": "high",
  "reasoning": "This theory describes a unique mechanism not covered by existing theories"
}}
"""
        
        try:
            # Call LLM
            response = self.llm_client.chat.completions.create(
                model=config.theory_llm_model,
                max_tokens=512,
                temperature=0.1,  # Low temperature for consistent classification
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            is_match = result.get('match', False)
            theory_number = result.get('theory_number')
            confidence = result.get('confidence', 'low')
            reasoning = result.get('reasoning', 'No reasoning provided')
            
            logger.debug(f"LLM classification result: {reasoning}")
            
            # Only accept high and medium confidence matches
            if is_match and theory_number and confidence in ['high', 'medium']:
                # theory_number is 1-based, convert to 0-based index
                idx = theory_number - 1
                if 0 <= idx < len(theories_to_check):
                    matched_theory = theories_to_check[idx]
                    return matched_theory, confidence
            
            return None, confidence
            
        except Exception as e:
            logger.error(f"LLM theory matching failed: {e}", exc_info=True)
            # Fallback to no match on error
            return None, "error"
    
    def _calculate_relevance_score(self, evidence_level: str) -> float:
        """
        Calculate relevance score based on evidence level
        
        Args:
            evidence_level: weak, moderate, or strong
            
        Returns:
            Score between 0 and 1
        """
        score_map = {
            "strong": 0.9,
            "moderate": 0.6,
            "weak": 0.3,
        }
        return score_map.get(evidence_level.lower(), 0.5)
    
    async def classify_article_theories(
        self,
        article_id: uuid.UUID,
        article_text: str,
        article_title: str = ""
    ) -> Dict:
        """
        Complete workflow: extract and classify theories for an article
        
        Args:
            article_id: UUID of the article
            article_text: Full text or abstract
            article_title: Title of the article
            
        Returns:
            Classification results
        """
        logger.info(f"Starting theory classification for article {article_id}")
        
        # Step 1: Extract theories from text
        extracted_theories = await self.extract_theories_from_text(
            article_text=article_text,
            article_title=article_title
        )
        
        if not extracted_theories:
            logger.info("No theories extracted from article")
            return {
                "status": "success",
                "linked_count": 0,
                "new_theories_count": 0,
                "theory_links": []
            }
        
        # Step 2: Classify and link theories
        result = await self.classify_and_link_theories(
            article_id=article_id,
            extracted_theories=extracted_theories
        )
        
        result["status"] = "success"
        return result

