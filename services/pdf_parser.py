from pathlib import Path
from typing import Optional, Tuple
import asyncio
import httpx
import pdfplumber
from loguru import logger
import re
from urllib.parse import urljoin

from config import config


class PDFParser:
    """
    Service for downloading and parsing PDF files
    """
    
    @staticmethod
    def _default_user_agent() -> str:
        """
        Build a polite User-Agent for NCBI resources.
        """
        contact = config.pmc_email or config.ncbi_email or config.pubmed_email
        if contact:
            return f"pmc-fetcher/1.0 (+mailto:{contact})"
        return "Mozilla/5.0 (compatible; PMCFetcher/1.0; +https://www.ncbi.nlm.nih.gov)"
    
    @staticmethod
    async def _resolve_pdf_download_url(url: str, client: httpx.AsyncClient) -> Tuple[str, Optional[str]]:
        """
        Resolve PMC stub URLs (ending with /pdf/) to the actual PDF asset.
        Returns the resolved URL and an optional referer to use for the download request.
        """
        if not url:
            return url, None
        
        normalized_url = url.strip()
        if not normalized_url:
            return url, None
        
        # If the URL already points to a PDF file, use it as-is
        lower_url = normalized_url.lower()
        if lower_url.endswith(".pdf") or ".pdf?" in lower_url:
            return normalized_url, None
        
        # Handle PMC article stub URLs like .../articles/PMC123456/pdf/
        pmc_match = re.search(r'/articles/(PMC\d+)', normalized_url, re.IGNORECASE)
        if not pmc_match:
            return normalized_url, None
        
        pmcid = pmc_match.group(1)
        article_page = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
        
        try:
            logger.debug(f"Resolving PDF asset for {pmcid} from article page")
            response = await client.get(
                article_page,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            response.raise_for_status()
            html = response.text
        except httpx.HTTPError as exc:
            logger.warning(f"Failed to resolve PMC PDF asset for {pmcid}: {exc}")
            # Fallback to direct download attempt with ?download=1
            fallback = urljoin(article_page, "pdf/?download=1")
            return fallback, article_page
        
        # Look for PDF links within the article page
        pdf_candidates = re.findall(r'href="([^"]+\.pdf[^"]*)"', html, re.IGNORECASE)
        for candidate in pdf_candidates:
            if pmcid in candidate or "/pdf/" in candidate:
                resolved = urljoin(article_page, candidate)
                logger.debug(f"Resolved PMC PDF URL for {pmcid}: {resolved}")
                return resolved, article_page
        
        # Final fallback: try standard download query
        fallback = urljoin(article_page, "pdf/?download=1")
        logger.debug(f"Using fallback PMC PDF URL for {pmcid}: {fallback}")
        return fallback, article_page
    
    @staticmethod
    async def download_pdf(url: str, filename: Optional[str] = None) -> Path:
        """
        Download PDF from URL
        
        Args:
            url: URL to download PDF from
            filename: Optional filename to save as
            
        Returns:
            Path to downloaded PDF file
        """
        # Create storage directory if it doesn't exist
        storage_path = Path(config.pdf_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            filename = f"{hash(url)}.pdf"
        
        file_path = storage_path / filename
        
        # Download PDF
        logger.info(f"Downloading PDF from {url}")
        
        base_headers = {
            "User-Agent": PDFParser._default_user_agent(),
            "Accept": "application/pdf,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True, headers=base_headers) as client:
            try:
                download_url, referer = await PDFParser._resolve_pdf_download_url(url, client)
                request_headers = dict(base_headers)
                if referer:
                    request_headers["Referer"] = referer
                
                response = await client.get(download_url, headers=request_headers)
                response.raise_for_status()
                
                # Save to file
                file_path.write_bytes(response.content)
                logger.info(f"PDF downloaded successfully: {file_path} (source: {download_url})")
                
                return file_path
                
            except httpx.HTTPError as e:
                logger.error(f"Failed to download PDF from {url}: {e}")
                raise
    
    @staticmethod
    async def extract_text_from_pdf(pdf_path: Path) -> str:
        """
        Extract text from PDF file using pdfplumber
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text content
        """
        logger.info(f"Extracting text from PDF: {pdf_path}")
        
        # Run PDF extraction in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, PDFParser._extract_text_sync, pdf_path)
        
        logger.info(f"Extracted {len(text)} characters from PDF")
        return text
    
    @staticmethod
    def _extract_text_sync(pdf_path: Path) -> str:
        """
        Synchronous PDF text extraction
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        text_parts = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    
                    # Log progress for large PDFs
                    if page_num % 10 == 0:
                        logger.debug(f"Processed {page_num}/{len(pdf.pages)} pages")
            
            full_text = "\n\n".join(text_parts)
            return full_text
            
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {pdf_path}: {e}")
            raise
    
    @staticmethod
    async def download_and_parse(url: str, filename: Optional[str] = None) -> tuple[str, Path]:
        """
        Download PDF and extract text in one operation
        
        Args:
            url: URL to download PDF from
            filename: Optional filename to save as
            
        Returns:
            Tuple of (extracted_text, pdf_path)
        """
        pdf_path = await PDFParser.download_pdf(url, filename)
        text = await PDFParser.extract_text_from_pdf(pdf_path)
        return text, pdf_path
    
    @staticmethod
    async def cleanup_pdf(pdf_path: Path) -> None:
        """
        Delete PDF file
        
        Args:
            pdf_path: Path to PDF file to delete
        """
        try:
            if pdf_path.exists():
                pdf_path.unlink()
                logger.info(f"Deleted PDF file: {pdf_path}")
        except Exception as e:
            logger.warning(f"Failed to delete PDF {pdf_path}: {e}")
