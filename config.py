import os

from dotenv import load_dotenv
load_dotenv()


def verify_env_var(var_name: str) -> str:
    """Verify if environment variable exists and return its value."""
    value = os.getenv(var_name)
    if value is None:
        raise EnvironmentError(f"Environment variable '{var_name}' is not set. Please set it in your .env file.")
    return value

# note: when writing in your own .env file - use the exact name as in "", for example "NCBI_EMAIL"
NCBI_EMAIL = verify_env_var("NCBI_EMAIL")
NCBI_API_KEY = verify_env_var("NCBI_API_KEY")

SCOPUS_TOKEN = verify_env_var("SCOPUS_TOKEN")

PMC_EMAIL = NCBI_EMAIL
PMC_API_KEY = NCBI_API_KEY
# PMC_EMAIL = verify_env_var("PMC_EMAIL")
# PMC_API_KEY = verify_env_var("PMC_API_KEY")

NATURE_EMAIL = verify_env_var("NATURE_EMAIL")

column_paper_url = 'paper_url'
column_paper_name = 'paper_name'
column_paper_year = 'paper_year'

column_abstract = 'abstract'
column_doi_url = 'doi_url'
column_keywords = 'keywords'
column_journal = 'journal'