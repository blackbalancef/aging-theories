# PubMed API Client

A simple Python client for accessing PubMed data using the NCBI E-utilities API.

## Features

- Search PubMed articles by query
- Fetch article details and summaries
- Retrieve full abstracts
- Parse article metadata (title, authors, journal, DOI, etc.)
- Respect NCBI rate limits

## Installation

Install dependencies using pip:

```bash
pip install requests
```

Or using uv:

```bash
uv pip install requests
```

## Quick Start

```python
from pubmed_client import PubMedClient

# Initialize the client (email is recommended by NCBI)
client = PubMedClient(email="your.email@example.com")

# Search for articles
pmids = client.search("COVID-19 vaccine", max_results=10)
print(f"Found {len(pmids)} articles")

# Fetch article details
articles = client.fetch_details(pmids)
for article in articles:
    print(article.get('title'))

# Or use the convenience method
articles = client.search_and_fetch("machine learning", max_results=5)
```

## Usage Examples

### Basic Search

```python
client = PubMedClient(email="your.email@example.com")
pmids = client.search("cancer immunotherapy", max_results=20)
```

### Fetch Article Summaries

```python
articles = client.search_and_fetch("CRISPR", max_results=5)
for article in articles:
    print(f"Title: {article.get('title')}")
    print(f"Journal: {article.get('fulljournalname')}")
    print(f"Date: {article.get('pubdate')}")
```

### Fetch Full Abstracts

```python
articles = client.search_and_fetch(
    "neural networks", 
    max_results=3, 
    include_abstracts=True
)
for article in articles:
    print(f"PMID: {article.get('pmid')}")
    print(f"Title: {article.get('title')}")
    print(f"Abstract: {article.get('abstract')}")
    print(f"DOI: {article.get('doi')}")
```

## API Methods

### `search(query, max_results=10, sort='relevance')`
Search PubMed and return a list of PMIDs.

### `fetch_details(pmids)`
Fetch article summaries for a list of PMIDs.

### `fetch_abstracts(pmids)`
Fetch full abstracts and detailed information for a list of PMIDs.

### `search_and_fetch(query, max_results=10, include_abstracts=False)`
Convenience method that combines search and fetch operations.

## Running the Example

```bash
python example.py
```

## Rate Limits

- Without API key: 3 requests per second
- With API key: 10 requests per second

To use an API key:

```python
client = PubMedClient(
    email="your.email@example.com",
    api_key="your_api_key"
)
```

Get an API key at: https://www.ncbi.nlm.nih.gov/account/

## Resources

- [PubMed E-utilities Documentation](https://www.ncbi.nlm.nih.gov/books/NBK25501/)
- [E-utilities Quick Start](https://www.ncbi.nlm.nih.gov/books/NBK25500/)

## License

MIT



