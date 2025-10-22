from typing import Dict, List, Optional


class CrawlerBase:
    """Abstract base class for all literature crawlers."""
    def search_with_history(self, query: str) -> tuple:
        raise NotImplementedError

    def fetch_records(self, count: int, webenv: str, query_key: str) -> List:
        raise NotImplementedError

    def build_queries(self) -> Dict[str, str]:
        raise NotImplementedError

    def parse_record(self, raw_record) -> Dict:
        raise NotImplementedError
