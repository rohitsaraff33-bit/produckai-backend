"""Sync Zoom recordings and transcripts."""

import argparse
import asyncio
import sys

import structlog

from apps.api.database import get_db_context
from apps.api.services.zoom_client import sync_zoom_recordings

logger = structlog.get_logger()


async def main(days_back: int = 30):
    """
    Sync Zoom recordings and transcripts to feedback database.

    Args:
        days_back: Number of days back to fetch recordings
    """
    logger.info("Starting Zoom sync", days_back=days_back)

    with get_db_context() as db:
        stats = await sync_zoom_recordings(db, days_back=days_back)

        if "error" in stats:
            logger.error("Zoom sync failed", error=stats["error"])
            print(f"❌ Error: {stats['error']}", file=sys.stderr)
            return 1

        logger.info("Zoom sync completed", stats=stats)
        print("\n✅ Zoom sync completed successfully!")
        print(f"   📹 Recordings found: {stats['recordings_found']}")
        print(f"   📝 Transcripts found: {stats['transcripts_found']}")
        print(f"   ➕ Feedback created: {stats['feedback_created']}")
        print(f"   🔄 Feedback updated: {stats['feedback_updated']}")

        if stats['errors'] > 0:
            print(f"   ⚠️  Errors: {stats['errors']}")

        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Zoom recordings and transcripts")
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days back to fetch recordings (default: 30)",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(main(days_back=args.days))
    sys.exit(exit_code)
