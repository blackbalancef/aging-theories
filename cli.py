#!/usr/bin/env python3
"""
CLI for managing the Aging Research Service
"""
import asyncio
import sys
from loguru import logger

from services.analysis_worker import start_worker
from agents.analysis_agent_worker import start_worker as start_agent_worker
from agents.discovery_agent import DiscoveryAgent
from db.database import get_db
from db.repository import DataSourceRepository


async def seed_data_sources():
    """
    Seed initial data sources in the database
    """
    logger.info("Seeding data sources...")
    
    sources = [
        {
            "source_name": "pubmed",
            "display_name": "PubMed",
            "requires_api_key": True,
            "api_client_class": "PubmedCrawler",
            "description": "PubMed is a database of biomedical literature",
            "is_active": True,
        },
        {
            "source_name": "pmc",
            "display_name": "PubMed Central (PMC)",
            "requires_api_key": True,
            "api_client_class": "PmcCrawler",
            "description": "PMC is a free full-text archive of biomedical literature",
            "is_active": True,
        },
        {
            "source_name": "scopus",
            "display_name": "Scopus",
            "requires_api_key": True,
            "api_client_class": "ScopusClient",
            "description": "Scopus is an abstract and citation database",
            "is_active": False,
        },
        {
            "source_name": "nature",
            "display_name": "Nature Publishing Group",
            "requires_api_key": True,
            "api_client_class": "NatureClient",
            "description": "Nature journal publications",
            "is_active": False,
        },
        {
            "source_name": "arxiv",
            "display_name": "arXiv",
            "requires_api_key": False,
            "api_client_class": "ArxivClient",
            "description": "arXiv is a preprint repository",
            "is_active": False,
        },
    ]
    
    async with get_db() as db:
        for source_data in sources:
            await DataSourceRepository.create_or_update(db, **source_data)
    
    logger.info(f"✓ Seeded {len(sources)} data sources")


async def init_db():
    """
    Initialize database tables using Alembic
    """
    import subprocess
    
    logger.info("Running database migrations...")
    
    try:
        result = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("✓ Database migrations completed")
        logger.info(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Database migration failed: {e}")
        logger.error(e.stderr)
        sys.exit(1)


def show_help():
    """
    Show CLI help
    """
    print("""
Aging Research Service - CLI

Commands:
    start-worker          Start the analysis worker (legacy)
    start-agent-worker    Start the Analysis Agent worker (recommended)
    discover <topic>      Discover articles using Discovery Agent
    init-db              Initialize database tables (run migrations)
    seed-sources         Seed initial data sources
    help                 Show this help message

Examples:
    python cli.py start-agent-worker
    python cli.py discover "mitochondrial dysfunction aging"
    python cli.py init-db
    python cli.py seed-sources
    """)


async def main():
    """
    Main CLI entry point
    """
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1]
    
    if command == "start-worker":
        logger.info("Starting analysis worker (legacy)...")
        await start_worker()
    elif command == "start-agent-worker":
        logger.info("Starting Analysis Agent worker...")
        await start_agent_worker()
    elif command == "discover":
        if len(sys.argv) < 3:
            logger.error("Please provide a topic to search for")
            print("Usage: python cli.py discover '<topic>'")
            sys.exit(1)
        
        topic = sys.argv[2]
        max_articles = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        
        logger.info(f"Starting discovery for: {topic} (max: {max_articles})")
        agent = DiscoveryAgent()
        result = await agent.discover_articles(topic, max_articles)
        
        logger.info("Discovery completed!")
        logger.info(f"Status: {result.get('status')}")
        logger.info(f"Statistics: {result.get('statistics')}")
        
    elif command == "init-db":
        await init_db()
    elif command == "seed-sources":
        await seed_data_sources()
    elif command == "help":
        show_help()
    else:
        logger.error(f"Unknown command: {command}")
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

