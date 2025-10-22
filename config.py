from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    # PubMed / NCBI configuration
    pubmed_api_key: str = ""
    pubmed_email: str = ""
    ncbi_email: str = ""
    ncbi_api_key: str = ""
    
    # AI model configuration
    nebius_api_key: str = ""
    llm_default_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    discovery_llm_model: str = ""
    analysis_llm_model: str = ""
    theory_llm_model: str = ""
    
    # Additional API keys
    scopus_token: str = ""
    nature_email: str = ""
    
    # PMC configuration (can use NCBI credentials)
    pmc_email: str = ""
    pmc_api_key: str = ""
    
    # Database configuration
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aging_research"
    
    # Redis configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_queue_name: str = "aging_research:article_analysis"
    
    # Service configuration
    pdf_storage_path: str = "data/pdfs"
    max_concurrent_analyses: int = 3
    worker_poll_interval: int = 5  # seconds
    
    # Agent configuration
    tavily_api_key: str = ""  # Optional for web search
    
    # Legacy configuration (for backward compatibility with old tools)
    # Note: TheoryClassificationService now uses LLM for theory matching instead
    theory_similarity_threshold: float = 0.85  # Deprecated: Used only by legacy tools
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"  # Deprecated: Used only by legacy tools

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        case_sensitive = False,
        extra = "ignore",
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set PMC credentials from NCBI if not provided
        if not self.pmc_email and self.ncbi_email:
            self.pmc_email = self.ncbi_email
        if not self.pmc_api_key and self.ncbi_api_key:
            self.pmc_api_key = self.ncbi_api_key
        # Support both naming conventions
        if not self.pubmed_api_key and self.ncbi_api_key:
            self.pubmed_api_key = self.ncbi_api_key
        if not self.pubmed_email and self.ncbi_email:
            self.pubmed_email = self.ncbi_email
        # Populate model overrides with sensible defaults
        if not self.discovery_llm_model:
            self.discovery_llm_model = self.llm_default_model
        if not self.analysis_llm_model:
            self.analysis_llm_model = self.llm_default_model
        if not self.theory_llm_model:
            self.theory_llm_model = self.llm_default_model

config = AppSettings()

# Legacy constants for backward compatibility with dev branch
NCBI_EMAIL = config.ncbi_email or config.pubmed_email
NCBI_API_KEY = config.ncbi_api_key or config.pubmed_api_key
SCOPUS_TOKEN = config.scopus_token
PMC_EMAIL = config.pmc_email or NCBI_EMAIL
PMC_API_KEY = config.pmc_api_key or NCBI_API_KEY
NATURE_EMAIL = config.nature_email

# CSV column names
column_paper_url = 'paper_url'
column_paper_name = 'paper_name'
column_paper_year = 'paper_year'
column_abstract = 'abstract'
column_doi_url = 'doi_url'
column_keywords = 'keywords'
column_journal = 'journal'

# Pricing for Nebius AI Studio models (per 1M tokens)
# https://nebius.com/pricing/ai-studio
MODEL_PRICING = {
    "meta-llama/Meta-Llama-3.1-8B-Instruct": {
        "input": 0.10,   # $0.10 per 1M input tokens
        "output": 0.10,  # $0.10 per 1M output tokens
    },
    "meta-llama/Meta-Llama-3.1-70B-Instruct": {
        "input": 0.80,
        "output": 0.80,
    },
    "meta-llama/Meta-Llama-3.1-405B-Instruct": {
        "input": 4.00,
        "output": 4.00,
    },
}
