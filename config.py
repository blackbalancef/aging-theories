from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    pubmed_api_key: str
    nebius_api_key: str
    pubmed_email: str = ""

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        case_sensitive = False,
        extra = "ignore",
    )
    
config = AppSettings()

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