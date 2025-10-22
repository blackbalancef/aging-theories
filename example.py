"""
Example usage of the PubMed API client
"""
from pubmed_client import PubMedClient


def main():
    # Initialize the client
    # It's recommended to provide your email (required by NCBI guidelines)
    client = PubMedClient(email="your.email@example.com")
    
    # Example 1: Simple search
    print("=" * 80)
    print("Example 1: Simple Search")
    print("=" * 80)
    query = "COVID-19 vaccine"
    pmids = client.search(query, max_results=5)
    print(f"Search query: '{query}'")
    print(f"Found {len(pmids)} articles")
    print(f"PMIDs: {pmids}\n")
    
    # Example 2: Search and fetch article summaries
    print("=" * 80)
    print("Example 2: Fetch Article Summaries")
    print("=" * 80)
    articles = client.search_and_fetch("machine learning healthcare", max_results=3)
    for i, article in enumerate(articles, 1):
        print(f"\nArticle {i}:")
        print(f"  UID: {article.get('uid', 'N/A')}")
        print(f"  Title: {article.get('title', 'N/A')}")
        print(f"  Authors: {', '.join(article.get('authors', [])[:3])}...")
        print(f"  Journal: {article.get('fulljournalname', 'N/A')}")
        print(f"  Pub Date: {article.get('pubdate', 'N/A')}")
    
    # Example 3: Fetch full abstracts
    print("\n" + "=" * 80)
    print("Example 3: Fetch Full Abstracts")
    print("=" * 80)
    articles_with_abstracts = client.search_and_fetch(
        "CRISPR gene editing", 
        max_results=2, 
        include_abstracts=True
    )
    for i, article in enumerate(articles_with_abstracts, 1):
        print(f"\nArticle {i}:")
        print(f"  PMID: {article.get('pmid', 'N/A')}")
        print(f"  Title: {article.get('title', 'N/A')}")
        print(f"  Authors: {', '.join(article.get('authors', [])[:3])}")
        print(f"  Journal: {article.get('journal', 'N/A')}")
        print(f"  Date: {article.get('publication_date', 'N/A')}")
        print(f"  DOI: {article.get('doi', 'N/A')}")
        abstract = article.get('abstract', 'N/A')
        if abstract and abstract != 'N/A':
            print(f"  Abstract: {abstract[:200]}...")
        else:
            print(f"  Abstract: Not available")


if __name__ == "__main__":
    main()



