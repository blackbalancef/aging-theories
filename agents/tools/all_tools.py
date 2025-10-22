# Import all tools for easy access

from agents.tools.web_search_tool import web_search_tools
from agents.tools.crawler_tool import crawler_tools
from agents.tools.crawl4ai_tool import crawl4ai_tools
from agents.tools.pdf_parser_tool import pdf_parser_tools
from agents.tools.database_tool import database_tools
from agents.tools.theory_extraction_tool import theory_extraction_tools


# Discovery agent tools (for finding articles)
discovery_tools = [
    *web_search_tools,
    *crawler_tools,
    *crawl4ai_tools,
    *database_tools,
]

# Analysis agent tools (for analyzing articles)
analysis_tools = [
    *pdf_parser_tools,
    *web_search_tools,  # For finding reviews
    *theory_extraction_tools,
    *database_tools,
]

# All tools combined
all_tools = [
    *web_search_tools,
    *crawler_tools,
    *crawl4ai_tools,
    *pdf_parser_tools,
    *database_tools,
    *theory_extraction_tools,
]

