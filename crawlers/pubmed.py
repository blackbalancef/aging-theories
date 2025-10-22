from typing import List, Dict, Optional, Any
from datetime import datetime
import time
import pandas as pd
from Bio import Entrez
import config
from input import input_reader
from pathlib import Path
from crawlers import base

class PubmedCrawler(base.CrawlerBase):
    """Crawler for PubMed literature."""

    def __init__(self, email: str, api_key: str,
                 max_papers: int = 100,
                 date_from: Optional[str] = None,
                 date_to: Optional[str] = None):
        """
        Initialize Pubmed handler with credentials and limits.

        Args:
            email: Email address for NCBI API
            api_key: NCBI API key
            max_papers: Maximum number of papers to retrieve
            date_from: Start date in YYYY/MM/DD format
            date_to: End date in YYYY/MM/DD format
        """
        self.email = email
        self.api_key = api_key
        self.max_papers = max_papers
        self.date_from = self._validate_date(date_from)
        self.date_to = self._validate_date(date_to)
        self.request_delay = 0.11 if api_key else 0.34
        self.db_list = ['pubmed', 'pmc', 'books', 'gene']
        self.pmids = set()  # Initialize set to track processed PMIDs

        Entrez.email = email
        Entrez.api_key = api_key

        print(f'N={self.max_papers}')

    def _validate_date(self, date_str: str) -> str:
        """
        Validate and format date string.

        Args:
            date_str: Date string in YYYY/MM/DD format

        Returns:
            str: Validated date string

        Raises:
            ValueError: If date format is invalid
        """
        try:
            if not date_str:
                return None
            date_obj = datetime.strptime(date_str, "%Y/%m/%d")
            return date_obj.strftime("%Y/%m/%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Use YYYY/MM/DD format")

    # def build_query(self) -> str:
    #     """
    #     Build a single search query based on topics and date range.
    #
    #     Returns:
    #         str: Formatted query string
    #     """
    #     if not input_reader.topics:
    #         raise ValueError("No topics defined in input_reader.py")
    #
    #     # Create topic queries
    #     topic_queries = [f'"{topic}"[Title/Abstract]' for topic in input_reader.topics]
    #     topic_part = '(' + ' OR '.join(topic_queries) + ')'
    #
    #     # Create date range query
    #     date_range = f'("{self.date_from}"[Date - Create] : "{self.date_to}"[Date - Create])'
    #
    #     # Combine queries
    #     return f"{topic_part} AND {date_range}"

    def build_queries(self) -> Dict[str, str]:
        """
        Build multiple search queries based on topics and date range.

        Returns:
            Dict[str, str]: Dictionary mapping query names to query strings
        """
        if not input_reader.topics:
            raise ValueError("No topics defined in input_reader.py")

        # Build queries from input_reader.topics
        topic_queries = {}
        for topic in input_reader.topics:
            # Clean topic for query key
            key = topic.lower().replace(' ', '_')
            # Create PubMed-specific query syntax
            query = f'"{topic}"[Title/Abstract]'
            topic_queries[f'topic_{key}'] = query

        # Add direct queries from input_reader if available
        direct_queries = input_reader.queries if hasattr(input_reader, 'queries') else {}

        # Combine all queries
        combined_queries = {**direct_queries, **topic_queries}

        # Add filters and date range
        final_queries = {}
        for key, query in combined_queries.items():
            filtered_query = f"({query})"

            # Add date range if specified
            if self.date_from or self.date_to:
                date_filter = ""
                if self.date_from:
                    date_filter += f'"{self.date_from}"[Date - Create] : '
                if self.date_to:
                    date_filter += f'"{self.date_to}"[Date - Create]'
                elif self.date_from:  # if only start date specified
                    date_filter += '"3000"[Date - Create]'  # arbitrary future date

                filtered_query = f"({filtered_query}) AND ({date_filter})"

            final_queries[key] = filtered_query

        return final_queries

    def search_with_history(self, query: str) -> tuple:
        """
        Search PubMed with the given query and return search history information.

        Args:
            query: PubMed search query string

        Returns:
            tuple: (count of results, WebEnv string, QueryKey string)
        """
        handle = Entrez.esearch(db='pubmed', term=query, usehistory="y", retmax=0)
        results = Entrez.read(handle)
        handle.close()
        count = int(results["Count"])

        # If max_papers is set, limit the count
        if self.max_papers and self.max_papers < count:
            count = self.max_papers

        return count, results["WebEnv"], results["QueryKey"]

    def parse_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Optional[str]]]:
        """
        Extract relevant information from a PubMed article record.

        Args:
            record: PubMed article record

        Returns:
            Optional[Dict[str, Optional[str]]]: Extracted article information or None if error
        """
        try:
            article = record['MedlineCitation']['Article']
            pmid = record['MedlineCitation']['PMID']

            # Skip if we've already processed this PMID
            if pmid in self.pmids:
                return None
            self.pmids.add(pmid)

            # Extract title
            title = article.get('ArticleTitle')

            # Extract year
            year = article.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {}).get('Year')

            # Extract abstract
            abstract = ''
            if 'Abstract' in article and 'AbstractText' in article['Abstract']:
                abstract_text = article['Abstract']['AbstractText']
                if isinstance(abstract_text, list):
                    abstract = ' '.join(abstract_text)
                else:
                    abstract = str(abstract_text)

            # Extract keywords (MeSH terms)
            keywords = ''
            if 'MeshHeadingList' in record['MedlineCitation']:
                keywords = ', '.join(
                    str(keyword['DescriptorName'])
                    for keyword in record['MedlineCitation']['MeshHeadingList']
                )

            # Create paper URL
            paper_url = f"https://www.ncbi.nlm.nih.gov/pubmed/{pmid}" if pmid else None

            # Extract DOI and create DOI URL
            doi = None
            if 'PubmedData' in record and 'ArticleIdList' in record['PubmedData']:
                for id_elem in record['PubmedData']['ArticleIdList']:
                    if hasattr(id_elem, 'attributes') and id_elem.attributes.get('IdType') == 'doi':
                        doi = str(id_elem)
                        break
            doi_url = f"https://doi.org/{doi}" if doi else None

            return {
                config.column_paper_url: paper_url,
                config.column_paper_name: title or None,
                config.column_paper_year: year,
                config.column_abstract: abstract,
                config.column_keywords: keywords,
                config.column_doi_url: doi_url,
            }

        except Exception as e:
            print(f"Error processing article: {str(e)}")
            return None

    def fetch_records(self, count: int, webenv: str, query_key: str) -> List[Dict[str, Optional[str]]]:
        """
        Fetch and process records from PubMed using the search history.

        Args:
            count: Number of records to fetch
            webenv: WebEnv string from search_with_history
            query_key: QueryKey string from search_with_history

        Returns:
            List[Dict[str, Optional[str]]]: List of processed records
        """
        all_records = []
        batch_size = 100  # Fetch in batches of 100

        for start in range(0, count, batch_size):
            try:
                handle = Entrez.efetch(
                    db="pubmed", rettype="medline", retmode="xml",
                    retstart=start, retmax=min(batch_size, count - start),
                    webenv=webenv, query_key=query_key)

                data = Entrez.read(handle, validate=False)
                handle.close()

                if 'PubmedArticle' in data:
                    for record in data['PubmedArticle']:
                        parsed = self.parse_record(record)
                        if parsed:
                            all_records.append(parsed)

                            # If we've reached max_papers, stop fetching
                            if self.max_papers and len(all_records) >= self.max_papers:
                                return all_records

                time.sleep(self.request_delay)

            except Exception as e:
                print(f"Error fetching PubMed batch starting at {start}: {e}")
                time.sleep(5)  # Wait longer after an error

        return all_records


    def run(self) -> pd.DataFrame:
        """
        Run the PubMed crawler and return results as a DataFrame.

        Returns:
            pd.DataFrame: DataFrame containing the fetched records
        """
        start_time = time.perf_counter()
        print(f"Started PubMed crawler at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Build queries
        queries = self.build_queries()

        # Initialize an empty list to store all records
        all_records = []

        # Process each query
        for query_name, query in queries.items():
            print(f"Processing query: {query_name}")

            # Search PubMed with history
            count, webenv, query_key = self.search_with_history(query)
            print(f"Found {count} results for query: {query_name}")

            if count > 0:
                # Fetch records
                records = self.fetch_records(count, webenv, query_key)
                all_records.extend(records)
                print(f"Fetched {len(records)} records for query: {query_name}")
            else:
                print(f"No records found for query: {query_name}")

        # Remove duplicates based on paper URL
        unique_records = []
        seen_urls = set()

        for record in all_records:
            url = record.get(config.column_paper_url, '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_records.append(record)

        print(f"Total unique records: {len(unique_records)}")

        # Convert to DataFrame
        df = pd.DataFrame(unique_records)

        execution_time = time.perf_counter() - start_time
        print(f"Execution time: {execution_time:.2f} seconds")

        return df

    def save_results(self, df: pd.DataFrame, output_path: str = 'examples_output/', file_prefix: str = 'pubmed_data') -> str:
        """
        Save DataFrame to a CSV file.

        Args:
            df: DataFrame to save
            output_path: Directory path to save the output file
            file_prefix: Prefix for the output filename

        Returns:
            str: Path to the saved file
        """
        # Create output directory if it doesn't exist
        Path(output_path).mkdir(parents=True, exist_ok=True)

        # Get the current date and time for the filename
        date_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M")

        # Save to CSV
        file_name = f"{output_path}{file_prefix}_{date_time_str}.csv"
        df.to_csv(file_name, index=False)
        print(f"Saved results to {file_name}")

        return file_name


def data_pubmed(retmax_number = 100) -> pd.DataFrame:
    """
    Legacy function that uses the PubmedCrawler class to maintain backward compatibility

    Args:
        retmax_number: Maximum number of records to retrieve

    Returns:
        pd.DataFrame: DataFrame containing the fetched records
    """
    # Create a PubmedCrawler instance with the same parameters
    crawler = PubmedCrawler(
        email=config.NCBI_EMAIL,
        api_key=config.NCBI_API_KEY,
        max_papers=retmax_number
    )

    # Run the crawler and return the DataFrame
    return crawler.run()
