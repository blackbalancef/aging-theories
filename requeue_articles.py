"""
Script to re-queue articles with PDF URLs that haven't been analyzed yet
"""
import asyncio
from loguru import logger

from db.database import get_db
from db.repository import ArticleRepository
from task_queue.task_queue import TaskQueue


async def requeue_unanalyzed_articles():
    """Find articles with PDF URLs but no analysis and add them to the queue"""

    logger.info("Finding articles with PDFs that need analysis...")

    async with get_db() as db:
        # Get articles with PDF URLs but no analysis
        articles = await ArticleRepository.get_unanalyzed_with_pdfs(db)

    if not articles:
        logger.info("No articles need to be queued for analysis")
        return 0

    logger.info(f"Found {len(articles)} articles to queue for analysis")

    # Queue each article
    queued = 0
    for article in articles:
        try:
            await TaskQueue.enqueue_article_task({
                "article_id": str(article.id),
                "doi": article.doi,
                "title": article.title,
                "abstract": article.abstract or "",
                "pdf_url": article.pdf_url,
                "full_text_url": article.full_text_url,
            })
            queued += 1
            logger.info(f"Queued: {article.title[:60]}...")
        except Exception as e:
            logger.error(f"Failed to queue article {article.id}: {e}")

    logger.info(f"Successfully queued {queued} articles for analysis")
    return queued


async def main():
    queued = await requeue_unanalyzed_articles()

    # Show queue stats
    stats = await TaskQueue.get_queue_stats()
    logger.info(f"Queue stats: {stats}")

    print(f"\n✓ Queued {queued} articles for analysis")
    print(f"✓ Current queue length: {stats['queue_length']}")


if __name__ == "__main__":
    asyncio.run(main())
