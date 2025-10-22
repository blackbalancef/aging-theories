from pydantic import BaseModel, Field
from typing import Literal

class BasePromptSchema(BaseModel):
    filename: str = Field(description="The filename of the prompt")

class ArticleClassificationRequest(BasePromptSchema):
    filename: Literal["article_classififcation.j2"] = "article_classififcation.j2"
    abstract_text: str = Field(description="The abstract text of the article")
    article_title: str = Field(description="The title of the article")

# Response schemas for structured outputs
class ArticleClassificationResponse(BaseModel):
    """Structured response for article classification"""
    is_aging_related: Literal["yes", "no"] = Field(
        description="Whether the article is primarily about aging research"
    )
    explanation: str = Field(
        description="Brief explanation (1-2 sentences) for the classification decision"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence level in the classification decision"
    )


class AgingTheoryAnalysisRequest(BasePromptSchema):
    """Request schema for detailed aging theory analysis"""
    filename: Literal["aging_theory_analysis.j2"] = "aging_theory_analysis.j2"
    abstract_text: str = Field(description="The abstract text of the article")
    article_title: str = Field(description="The title of the article")


class AgingTheoryAnalysisResponse(BaseModel):
    """Structured response for aging theory analysis with 9 key questions"""
    q1_biomarker: Literal["Yes", "No"] = Field(
        description="Does the paper/theory suggest an aging biomarker?"
    )
    q1_explanation: str = Field(
        description="Brief explanation for Q1"
    )
    
    q2_molecular_mechanism: Literal["Yes", "No"] = Field(
        description="Does the paper/theory suggest a molecular mechanism of aging?"
    )
    q2_explanation: str = Field(
        description="Brief explanation for Q2"
    )
    
    q3_longevity_intervention: Literal["Yes", "No"] = Field(
        description="Does the paper/theory suggest a longevity intervention to test?"
    )
    q3_explanation: str = Field(
        description="Brief explanation for Q3"
    )
    
    q4_aging_irreversible: Literal["Yes", "No"] = Field(
        description="Does the paper/theory claim that aging cannot be reversed?"
    )
    q4_explanation: str = Field(
        description="Brief explanation for Q4"
    )
    
    q5_species_lifespan_biomarker: Literal["Yes", "No"] = Field(
        description="Does the paper/theory suggest a biomarker that explains differences in maximum lifespan between species?"
    )
    q5_explanation: str = Field(
        description="Brief explanation for Q5"
    )
    
    q6_naked_mole_rat: Literal["Yes", "No"] = Field(
        description="Does the paper/theory explain why the naked mole rat can live 40+ years despite its small size?"
    )
    q6_explanation: str = Field(
        description="Brief explanation for Q6"
    )
    
    q7_bird_longevity: Literal["Yes", "No"] = Field(
        description="Does the paper/theory explain why birds live much longer than mammals on average?"
    )
    q7_explanation: str = Field(
        description="Brief explanation for Q7"
    )
    
    q8_size_lifespan: Literal["Yes", "No"] = Field(
        description="Does the paper/theory explain why large animals live longer than small ones?"
    )
    q8_explanation: str = Field(
        description="Brief explanation for Q8"
    )
    
    q9_calorie_restriction: Literal["Yes", "No"] = Field(
        description="Does the paper/theory explain why calorie restriction increases the lifespan of vertebrates?"
    )
    q9_explanation: str = Field(
        description="Brief explanation for Q9"
    )
