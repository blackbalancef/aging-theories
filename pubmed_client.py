"""
PubMed API Client using NCBI E-utilities API
"""
import time
from typing import List, Dict, Optional
import requests
from urllib.parse import urlencode


class PubMedClient:
    """
    A simple client for interacting with the PubMed E-utilities API.
    
    Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the PubMed client.
        
        Args:
            email: Your email address (recommended by NCBI)
            api_key: Your NCBI API key (optional, increases rate limits)
        """
        self.email = email
        self.api_key = api_key
        self.session = requests.Session()
        
    def _build_params(self, **kwargs) -> Dict:
        """Build common parameters for API requests."""
        params = {
            'retmode': 'json',
        }
        if self.email:
            params['email'] = self.email
        if self.api_key:
            params['api_key'] = self.api_key
        params.update(kwargs)
        return params
    
    def search(self, query: str, max_results: int = 10, 
               sort: str = 'relevance') -> List[str]:
        """
        Search PubMed for articles matching a query.
        
        Args:
            query: Search query (e.g., "cancer immunotherapy")
            max_results: Maximum number of results to return
            sort: Sort order ('relevance', 'pub_date', 'Author', etc.)
            
        Returns:
            List of PubMed IDs (PMIDs)
        """
        url = f"{self.BASE_URL}/esearch.fcgi"
        params = self._build_params(
            db='pubmed',
            term=query,
            retmax=max_results,
            sort=sort
        )
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        return data.get('esearchresult', {}).get('idlist', [])
    
    def fetch_details(self, pmids: List[str]) -> List[Dict]:
        """
        Fetch detailed information for a list of PubMed IDs.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of article details
        """
        if not pmids:
            return []
        
        url = f"{self.BASE_URL}/esummary.fcgi"
        params = self._build_params(
            db='pubmed',
            id=','.join(pmids)
        )
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        result = data.get('result', {})
        
        articles = []
        for pmid in pmids:
            if pmid in result:
                articles.append(result[pmid])
        
        return articles
    
    def fetch_abstracts(self, pmids: List[str]) -> List[Dict]:
        """
        Fetch full abstracts and detailed information for PubMed IDs.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of articles with abstracts
        """
        if not pmids:
            return []
        
        url = f"{self.BASE_URL}/efetch.fcgi"
        params = self._build_params(
            db='pubmed',
            id=','.join(pmids),
            retmode='xml'
        )
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        # Parse XML to extract key information
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        articles = []
        for article in root.findall('.//PubmedArticle'):
            article_data = self._parse_article_xml(article)
            articles.append(article_data)
        
        return articles
    
    def _parse_article_xml(self, article_element) -> Dict:
        """Parse XML element to extract article information."""
        data = {}
        
        # Get PMID
        pmid_elem = article_element.find('.//PMID')
        data['pmid'] = pmid_elem.text if pmid_elem is not None else None
        
        # Get title
        title_elem = article_element.find('.//ArticleTitle')
        data['title'] = title_elem.text if title_elem is not None else None
        
        # Get abstract
        abstract_texts = article_element.findall('.//AbstractText')
        if abstract_texts:
            abstract_parts = []
            for abstract_text in abstract_texts:
                label = abstract_text.get('Label', '')
                text = abstract_text.text or ''
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            data['abstract'] = ' '.join(abstract_parts)
        else:
            data['abstract'] = None
        
        # Get authors
        authors = []
        for author in article_element.findall('.//Author'):
            last_name = author.find('LastName')
            fore_name = author.find('ForeName')
            if last_name is not None and fore_name is not None:
                authors.append(f"{fore_name.text} {last_name.text}")
        data['authors'] = authors
        
        # Get journal
        journal_elem = article_element.find('.//Journal/Title')
        data['journal'] = journal_elem.text if journal_elem is not None else None
        
        # Get publication date
        pub_date = article_element.find('.//PubDate')
        if pub_date is not None:
            year = pub_date.find('Year')
            month = pub_date.find('Month')
            day = pub_date.find('Day')
            date_parts = []
            if year is not None:
                date_parts.append(year.text)
            if month is not None:
                date_parts.append(month.text)
            if day is not None:
                date_parts.append(day.text)
            data['publication_date'] = ' '.join(date_parts)
        else:
            data['publication_date'] = None
        
        # Get DOI
        doi_elem = article_element.find('.//ArticleId[@IdType="doi"]')
        data['doi'] = doi_elem.text if doi_elem is not None else None
        
        return data
    
    def search_and_fetch(self, query: str, max_results: int = 10, 
                        include_abstracts: bool = False) -> List[Dict]:
        """
        Convenience method to search and fetch article details in one call.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            include_abstracts: If True, fetch full abstracts (slower)
            
        Returns:
            List of article details
        """
        pmids = self.search(query, max_results=max_results)
        
        if not pmids:
            return []
        
        # Respect NCBI rate limits (3 requests per second without API key)
        time.sleep(0.34)
        
        if include_abstracts:
            return self.fetch_abstracts(pmids)
        else:
            return self.fetch_details(pmids)


