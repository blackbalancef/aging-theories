from typing import Tuple
from langchain_core.tools import tool
from loguru import logger

from services.pdf_parser import PDFParser


@tool
async def parse_pdf_from_url(pdf_url: str, cleanup: bool = True) -> str:
    """
    Download and parse a PDF from URL to extract full text.
    
    Args:
        pdf_url: URL to the PDF file
        cleanup: Whether to delete PDF file after parsing (default: True)
        
    Returns:
        Extracted text from the PDF
    """
    try:
        logger.info(f"Parsing PDF from: {pdf_url}")
        
        # Download and parse
        full_text, pdf_path = await PDFParser.download_and_parse(pdf_url)
        
        if not full_text or len(full_text) < 100:
            logger.warning(f"PDF extraction yielded little content from {pdf_url}")
            if cleanup and pdf_path:
                await PDFParser.cleanup_pdf(pdf_path)
            return f"Error: PDF extraction failed or yielded minimal content from {pdf_url}"
        
        # Cleanup if requested
        if cleanup and pdf_path:
            await PDFParser.cleanup_pdf(pdf_path)
        
        # Limit text size for tool output
        if len(full_text) > 10000:
            logger.info(f"Truncating text from {len(full_text)} to 10000 chars for tool output")
            text_preview = full_text[:10000]
            return (
                f"Successfully extracted {len(full_text)} characters from PDF.\n\n"
                f"First 10000 characters:\n\n{text_preview}\n\n"
                f"[Text truncated for display, full text available]"
            )
        
        return f"Successfully extracted text from PDF:\n\n{full_text}"
        
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        return f"Error parsing PDF: {str(e)}"


# Export tools
pdf_parser_tools = [parse_pdf_from_url]

