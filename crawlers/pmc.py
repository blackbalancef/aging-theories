import time
from typing import Dict, List, Optional
from datetime import datetime
import random
from Bio import Entrez

import config
from input import input_reader
from crawlers import base


from typing import Optional, Dict, Any
# from logging import getLogger

# logger = getLogger(__name__)


class PmcCrawler(base.CrawlerBase):
    """Crawler for PMC literature."""
    def __init__(self, email: str, api_key: Optional[str] = None,
                 date_from: Optional[str] = None, date_to: Optional[str] = None,
                 max_papers: Optional[int] = None):
        """
           Initialize PMC crawler with optional date range and paper limit


           Args:
               email: Required email for NCBI
               api_key: Optional NCBI API key
               date_from: Optional start date in YYYY/MM/DD format
               date_to: Optional end date in YYYY/MM/DD format
               max_papers: Optional maximum number of papers to retrieve

           Returns:
               None

           Example:
                # >>> crawler = PmcCrawler(email="your@email.com", date_from="2023/01/01", date_to="2023/12/31") # Get all papers from 2023
                #
                # >>> crawler = PmcCrawler(email="your@email.com", date_from="2020/01/01", max_papers=500) # Get max 500 papers from the last 5 years
                #
                # >>> crawler = PmcCrawler(email="your@email.com", max_papers=100) # Get max 100 papers (random selection if more available)
        """
        Entrez.email = email
        if api_key:
            Entrez.api_key = api_key
            self.request_delay = 0.34
        else:
            self.request_delay = 1.0
        self.pmids = set()
        self.date_from = self._validate_date(date_from)
        self.date_to = self._validate_date(date_to)
        self.max_papers = max_papers
        print(f'N={self.max_papers}')

    def _validate_date(self, date_str: Optional[str]) -> Optional[str]:
        """Validate and format date string"""
        if not date_str:
            return None
        try:
            # Convert to datetime to validate and standardize format
            date_obj = datetime.strptime(date_str, "%Y/%m/%d")
            return date_obj.strftime("%Y/%m/%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Use YYYY/MM/DD format")

    def build_queries(self) -> Dict[str, str]:
        # PMC-specific queries—focus on open access full-text

        if not input_reader.topics:
            raise ValueError("No topics defined in input_reader.py")

        # Build queries from input_reader.topics
        topic_queries = {}
        for topic in input_reader.topics:
            # Clean topic for query key
            key = topic.lower().replace(' ', '_')
            # Create PMC-specific query syntax
            query = f'"{topic}"[Title/Abstract]'
            topic_queries[f'topic_{key}'] = query

        direct_queries = input_reader.queries
        # direct_queries = {
        #     'aging_theories_general': '"aging theory"[Title/Abstract] OR "aging theories"[Title/Abstract]',
        #     'aging_mechanisms': '"mechanisms of aging"[Title/Abstract] OR "aging mechanisms"[Title/Abstract]',
        #     'biogerontology': '"biogerontology"[Title/Abstract] OR "biological aging"[Title/Abstract]',
        #     'senescence_theories': '"cellular senescence"[Title/Abstract] AND "theory"[Title/Abstract]'
        # }

        # Combine all queries
        combined_queries = {**direct_queries, **topic_queries}

        # Add filters and date range
        final_queries = {}
        for key, query in combined_queries.items():
            # Add PMC-specific filters
            # todo: query filtering
            # filtered_query = f"({query}) AND open access[filter]"
            filtered_query = f"({query})"

            # Add date range if specified
            if self.date_from or self.date_to:
                date_filter = ""
                if self.date_from:
                    date_filter += f'"{self.date_from}"[PDAT] : '
                if self.date_to:
                    date_filter += f'"{self.date_to}"[PDAT]'
                elif self.date_from:  # if only start date specified
                    date_filter += '"3000"[PDAT]'  # arbitrary future date

                filtered_query = f"({filtered_query}) AND ({date_filter})"

            final_queries[key] = filtered_query

        return final_queries

    def search_with_history(self, query: str) -> tuple:
        handle = Entrez.esearch(db='pmc', term=query, usehistory="y", retmax=0)
        results = Entrez.read(handle)
        handle.close()
        count = int(results["Count"])

        # If max_papers is set, limit the count
        if self.max_papers and self.max_papers < count:
            count = self.max_papers

        return count, results["WebEnv"], results["QueryKey"]

    def extract_pmcid_and_doi(self, article_id_list):
        pmcid, doi = None, None
        if not article_id_list:
            return None, None
        if isinstance(article_id_list, dict):  # normalize to list
            article_id_list = [article_id_list]
        for elem in article_id_list:
            id_type = elem.get('pub-id-type') if isinstance(elem, dict) else None
            value = elem.get('#text') if isinstance(elem, dict) else str(elem)
            if id_type == 'pmcid' and not pmcid:
                pmcid = value
            if id_type == 'doi' and not doi:
                doi = value
        return pmcid, doi

    def get_clean_abstract(self, meta, flatten: bool = True):
        """
        Extract an abstract from a PMC 'article-meta' section.
        Supports structured (Background, Methods, etc.) and plain abstracts.

        Args:
            meta (dict): The 'article-meta' dictionary from the PMC record.
            flatten (bool): If True, joins structured sections into one text string.

        Returns:
            Optional[str]: Clean abstract as plain text. Returns None if missing.
        """
        abstract_section = meta.get('abstract', []) if meta else []
        if isinstance(abstract_section, dict):
            abstract_section = [abstract_section]
        if not abstract_section or not isinstance(abstract_section, list):
            return None

        structured_sections = []  # Changed from dict to list
        paragraphs = []

        for item in abstract_section:
            if not isinstance(item, dict):
                continue
            title = item.get('title')
            content = item.get('p', [])
            if isinstance(content, str):
                content = [content]
            text = ' '.join(content)
            if title:
                structured_sections.append(f"{title}: {text.strip()}")
            elif text:
                paragraphs.append(text.strip())

        if structured_sections:
            return ' '.join(structured_sections) if flatten else {s.split(':', 1)[0]: s.split(':', 1)[1].strip()
                                                               for s in structured_sections}
        if paragraphs:
            return '\n\n'.join(paragraphs)
        return None


    def extract_year(self, meta):
        pub_dates = meta.get('pub-date', [])
        if isinstance(pub_dates, dict):
            pub_dates = [pub_dates]
        for item in pub_dates:
            if isinstance(item, dict) and 'year' in item:
                val = item['year']
                if isinstance(val, list):
                    val = val[0]
                val = str(val)
                if val.isdigit() and len(val) == 4:
                    return val
            if isinstance(item, list) and len(item) >= 3:
                val = str(item[2])
                if val.isdigit() and len(val) == 4:
                    return val
        return str(meta.get("copyright-year", "NA"))

    def get_keywords(self, meta):
        # Extract keywords
        keywords = []
        kwd_group = meta.get('kwd-group', [])
        if isinstance(kwd_group, dict):
            kwd_group = [kwd_group]

        for group in kwd_group:
            if isinstance(group, dict):
                kwds = group.get('kwd', [])
                if isinstance(kwds, str):
                    keywords.append(kwds)
                elif isinstance(kwds, list):
                    keywords.extend(kwds)

        # Also check for MeSH terms
        mesh_terms = meta.get('article-categories', {}).get('subj-group', [])
        if isinstance(mesh_terms, dict):
            mesh_terms = [mesh_terms]

        for term_group in mesh_terms:
            if isinstance(term_group, dict):
                terms = term_group.get('subject', [])
                if isinstance(terms, str):
                    keywords.append(terms)
                elif isinstance(terms, list):
                    keywords.extend(terms)

        # Clean and join keywords
        keywords = [str(k).strip() for k in keywords if k]
        keywords_str = '; '.join(keywords) if keywords else None
        return keywords_str

    def fetch_records(self, count: int, webenv: str, query_key: str) -> List:
        all_records = []
        # todo: work with batch_size
        batch_size = 100

        # If max_papers is set, potentially randomize which records to fetch
        if self.max_papers and self.max_papers < count:
            # Get random starting points that will cover max_papers
            starts = random.sample(range(0, count - batch_size),
                                   min(count // batch_size,
                                       (self.max_papers + batch_size - 1) // batch_size))
        else:
            starts = range(0, count, batch_size)

        for start in starts:
            try:
                handle = Entrez.efetch(
                    db="pmc", retmode="xml", retstart=start,
                    retmax=min(batch_size, self.max_papers - len(all_records)) if self.max_papers else batch_size,
                    webenv=webenv, query_key=query_key)
                results = Entrez.read(handle, validate=False)
                handle.close()

                if isinstance(results, list):
                    articles = results
                elif isinstance(results, dict):
                    articles = results.get('article', []) or results.get('article-set', []) or []
                    if isinstance(articles, dict):
                        articles = [articles]
                else:
                    articles = []

                for rec in articles:
                    # print(rec)
                    parsed = self.parse_record(rec)
                    if parsed:
                        all_records.append(parsed)
                        if self.max_papers and len(all_records) >= self.max_papers:
                            return all_records

                time.sleep(self.request_delay)
            except Exception as e:
                print(f"Error fetching/crawling PMC batch at {start}: {e}")
                time.sleep(5)

        return all_records

    def parse_record(self, rec: Dict[str, Any]) -> Optional[Dict[str, Optional[str]]]:
        """Parse record and extract relevant fields.

        Args:
            rec: Dictionary containing article data

        Returns:
            Dictionary with parsed fields or None if parsing fails
        """
        # if not isinstance(rec, dict):
        #     logger.error("Invalid record format: expected dict")
        #     return None

        try:
            meta = rec.get('front', {}).get('article-meta', {})

            # Extract article IDs
            article_ids = meta.get('article-id', [])
            pmcid = pmid = doi = None

            for id_elem in article_ids:
                if not hasattr(id_elem, 'attributes'):
                    continue

                id_type = id_elem.attributes.get('pub-id-type')
                try:
                    id_value = str(id_elem)
                except (ValueError, TypeError):
                    continue

                if id_type == 'pmcid':
                    pmcid = id_value
                elif id_type == 'pmid':
                    pmid = id_value
                elif id_type == 'doi':
                    doi = id_value

            paper_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid else None
            doi_url = f"https://doi.org/{doi}" if doi else None

            title = meta.get('title-group', {}).get('article-title', '') if meta else rec.get('article-title', '')
            year = self.extract_year(meta) if meta else None  # Changed 'NA' to None for consistency
            abstract = self.get_clean_abstract(meta)
            keywords = self.get_keywords(meta) if meta else None

            return {
                config.column_paper_url: paper_url,
                config.column_paper_name: title or None,
                config.column_paper_year: year,
                config.column_abstract: abstract,
                config.column_keywords: keywords,
                config.column_doi_url: doi_url,
            }
        except Exception as e:
            print(f"Error parsing PMC record: {str(e)}")
            return {}
        # except Exception as e:
        #     logger.error(f"Error parsing PMC record: {str(e)}")
        #     return None

