import time
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import requests
from Bio import Entrez

import config
from crawlers import base
from input import input_reader


class PubMedCrawler(base.CrawlerBase):
    """Crawler for PubMed literature."""
    def __init__(self, email: str, api_key: Optional[str] = None):
        Entrez.email = email
        if api_key:
            Entrez.api_key = api_key
            self.request_delay = 0.34  # 3/sec with key
        else:
            self.request_delay = 1.0  # 1/sec without
        self.pmids = set()

    def build_queries(self) -> Dict[str, str]:
        # Pasted queries
        result = input_reader.queries
        return result

    def search_with_history(self, query: str) -> tuple:
        # PubMed Entrez logic
        handle = Entrez.esearch(db='pubmed', term=query, usehistory="y", retmax=0)
        results = Entrez.read(handle)
        handle.close()
        return int(results["Count"]), results["WebEnv"], results["QueryKey"]

    def fetch_records(self, count: int, webenv: str, query_key: str) -> List:
        # Batch fetching for PubMed
        all_records = []
        for start in range(0, count, 500):
            try:
                handle = Entrez.efetch(
                    db="pubmed", rettype="medline", retmode="xml",
                    retstart=start, retmax=500, webenv=webenv, query_key=query_key)
                data = Entrez.read(handle, validate=False)
                handle.close()
                if 'PubmedArticle' in data:
                    for record in data['PubmedArticle']:
                        parsed = self.parse_record(record)
                        if parsed:
                            all_records.append(parsed)
                time.sleep(self.request_delay)
            except Exception as e:
                print(f"Error fetching PubMed batch starting at {start}: {e}")
                time.sleep(5)
        return all_records

    def parse_record(self, record) -> Dict:
        # Parse PubMed XML
        try:
            article = record['MedlineCitation']['Article']
            pmid = str(record['MedlineCitation']['PMID'])
            if pmid in self.pmids:
                return None
            self.pmids.add(pmid)
            paper_url = ''
            paper_name = str(article.get('ArticleTitle', ''))
            paper_year = article['Journal']['JournalIssue']['PubDate'].get('Year', '')
            abstract_list = article.get('Abstract', {}).get('AbstractText', [])
            abstract = ' '.join([str(text) for text in abstract_list])
            # journal = str(article['Journal'].get('Title', ''))
            # todo: add keywords
            return {
                config.column_paper_url:paper_url,
                config.column_paper_name: paper_name,
                config.column_paper_year: paper_year,
                config.column_abstract: abstract,
                # config.column_journal: journal,
                # 'pmid': pmid,
                # 'source': 'PubMed',
            }
        except Exception as e:
            print(f"Error parsing PubMed record: {e}")
            return None


class NatureCrawler(base.CrawlerBase):
    """
    Limitations:
        No free bulk API; scraping is rate-limited, risky, and not recommended
        unless Tom authorized – can get blocked.
        Usually, you need to use CrossRef or Nature’s own APIs
        (possible for abstracts, metadata);
        always respect robots.txt and publisher terms.
        Best Practice: Use publisher APIs or CrossRef’s API for metadata,
        never scrape HTML without permission.
    """
    def __init__(self, email: str):
        self.email = email
        self.results = []

    def build_queries(self) -> Dict[str, str]:
        # todo: add queries for Nature
        return {
            'aging_theories_nature':
            'aging theories'
        }

    def search_with_history(self, query: str) -> tuple:
        # Just get count - CrossRef might paginate
        url = f"https://api.crossref.org/works?filter=publisher-name:Nature,title:{query}&rows=0"
        r = requests.get(url)
        count = r.json()['message']['total-results']
        return count, None, None

    def fetch_records(self, count: int, webenv: str, query_key: str) -> List:
        all_records = []
        batch_size = 100
        for offset in range(0, count, batch_size):
            url = f"https://api.crossref.org/works?filter=publisher-name:Nature,title:aging theories&rows={batch_size}&offset={offset}"
            try:
                r = requests.get(url)
                items = r.json()['message']['items']
                for item in items:
                    parsed = self.parse_record(item)
                    if parsed:
                        all_records.append(parsed)
                time.sleep(1.0)  # Respect rate limits!
            except Exception as e:
                print(f"Nature fetch error at offset {offset}: {e}")
                time.sleep(5)
        return all_records

    def parse_record(self, record) -> Dict:
        try:
            # todo: make a paper_url, columns form config
            return {
                'paper_name': record.get('title', [''])[0],
                'paper_year': record.get('issued', {}).get('date-parts', [['']])[0][0],
                'abstract': record.get('abstract', ''),
                # 'journal': record.get('container-title', [''])[0]
                # 'source': 'Nature',
                # 'doi': record.get('DOI'),
            }
        except Exception as e:
            print(f"Nature parse error: {e}")
            return None


class ScopusCrawler(base.CrawlerBase):
    """Crawler for Scopus (hypothetical, for expansion only)."""
    def __init__(self, api_token: str):
        self.api_token = api_token
        # ... other Scopus init

    def build_queries(self) -> Dict[str, str]:
        # Scopus-style queries
        pass

    def search_with_history(self, query: str) -> tuple:
        # Scopus search logic
        pass

    def fetch_records(self, count: int, webenv: str, query_key: str) -> List:
        # Scopus batch fetching
        pass

    def parse_record(self, raw_record) -> Dict:
        # Parse Scopus JSON/XML
        pass


class AgingTheoryCrawler:
    """Master controller for aging theory paper collection across sources."""

    def __init__(self, crawlers: List[base.CrawlerBase]):
        self.crawlers = crawlers

    def standardize_record(self, rec: Dict) -> Dict:
        """Standardize column names across different crawlers."""
        if not rec:
            return None

        # todo: might remove later
        # Define standard column names
        standard_columns = {
            'paper_url': config.column_paper_url,
            'paper_name': config.column_paper_name,
            'paper_year': config.column_paper_year,
            'doi_url': config.column_doi_url,
            'abstract': config.column_abstract,
            'keywords': config.column_keywords,
            'journal': config.column_journal,
            'pmid': 'pmid',
            'source': 'source',
            'doi': 'doi'
        }

        # Create a new standardized record
        standardized = {}

        # Map old keys to new standardized keys
        for old_key, new_key in standard_columns.items():
            if old_key in rec:
                standardized[new_key] = rec[old_key]
            elif new_key in rec:
                standardized[new_key] = rec[new_key]

        return standardized

    def run_comprehensive_search(self, max_per_query: Optional[int] = None) -> pd.DataFrame:
        all_records = []
        unique_keys = set()

        for crawler in self.crawlers:
            print(f"\nRunning crawler: {crawler.__class__.__name__}")
            queries = crawler.build_queries()

            for query_name, query in queries.items():
                print(f"\nProcessing query '{query_name}': {query}")
                count, webenv, query_key = crawler.search_with_history(query)
                print(f"Found {count} results")

                if not count:
                    continue

                records = crawler.fetch_records(count, webenv, query_key)
                print(f"Fetched {len(records)} records")

                # Print debug info
                if records and len(records) > 0:
                    print(f"Sample record keys: {list(records[0].keys())}")

                # Process each record
                for rec in records:
                    if not rec:
                        continue

                    # Create a copy to avoid modifying the original
                    processed_rec = rec.copy()

                    # Generate a unique identifier
                    identifiers = [
                        processed_rec.get(config.column_doi_url),
                        processed_rec.get(config.column_paper_url),
                        processed_rec.get(config.column_paper_name)  # Use title as last resort
                    ]

                    # Use the first non-None identifier
                    key = next((str(k) for k in identifiers if k is not None), None)

                    if key:
                        if key not in unique_keys:
                            # Ensure all required columns exist (with None if missing)
                            required_columns = [
                                config.column_paper_url,
                                config.column_paper_name,
                                config.column_paper_year,
                                config.column_abstract,
                                config.column_keywords,
                                config.column_doi_url,
                                # config.column_journal
                            ]

                            for col in required_columns:
                                if col not in processed_rec:
                                    processed_rec[col] = None

                            # Remove PMID if it exists
                            if 'pmid' in processed_rec:
                                del processed_rec['pmid']

                            # Check if paper_url exists and is not None
                            if not processed_rec.get(config.column_paper_url):
                                # Try to construct paper_url from other information
                                if processed_rec.get(config.column_doi_url):
                                    processed_rec[config.column_paper_url] = processed_rec[config.column_doi_url]

                            all_records.append(processed_rec)
                            unique_keys.add(key)
                    else:
                        print(f"Warning: Record without any identifier found: {processed_rec}")

        print(f"\nTotal records collected: {len(all_records)}")

        if not all_records:
            print("Warning: No records found!")
            return pd.DataFrame()

        df = pd.DataFrame(all_records)
        print(f"DataFrame columns: {list(df.columns)}")
        print(f"DataFrame shape: {df.shape}")

        return df

    def save_results(self, df: pd.DataFrame, base_filename: str = 'aging_theories_papers'):
        """Save results in multiple formats."""
        # Print debug info
        print("\nDataFrame Info:")
        print(df.info())

        date_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M")  # Example: '2025-10-19_22-13'
        # CSV
        path = "data_output/"
        csv_file = f"{path}{base_filename}_{date_time_str}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"Saved CSV: {csv_file} ({len(df)} papers)")

        # Summary statistics
        print(f"\nSummary Statistics:")
        print(f"  Papers total: {len(df)}")
        print(f"  Available columns: {list(df.columns)}")

        # Check for column existence before accessing
        if config.column_abstract in df.columns:
            print(f"  Papers with abstracts: {df['abstract'].notna().sum()}")
        else:
            print("  No abstract column found in the data")

        if config.column_doi_url in df.columns:
            print(f"  Papers with DOI: {df[config.column_doi_url].notna().sum()}")
        else:
            print("  No DOI URL column found in the data")

        if config.column_keywords in df.columns:
            print(f"  Papers with keywords: {df[config.column_keywords].notna().sum()}")
        else:
            print("  No keywords column found in the data")
