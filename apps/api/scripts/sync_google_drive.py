"""Sync Google Drive documents."""

import argparse
import asyncio
import sys

import structlog

from apps.api.database import get_db_context
from apps.api.services.google_client import sync_google_docs

logger = structlog.get_logger()


async def main(folder_ids: list):
    """
    Sync Google Drive documents to feedback database.

    Args:
        folder_ids: List of Google Drive folder IDs
    """
    logger.info("Starting Google Drive sync", folder_ids=folder_ids)

    with get_db_context() as db:
        stats = await sync_google_docs(db, folder_ids=folder_ids)

        if "error" in stats:
            logger.error("Google Drive sync failed", error=stats["error"])
            print(f"❌ Error: {stats['error']}", file=sys.stderr)
            return 1

        logger.info("Google Drive sync completed", stats=stats)
        print("\n✅ Google Drive sync completed successfully!")
        print(f"   📁 Files found: {stats['files_found']}")
        print(f"   📄 Documents processed: {stats['documents_processed']}")
        print(f"   ➕ Feedback created: {stats['feedback_created']}")
        print(f"   🔄 Feedback updated: {stats['feedback_updated']}")

        if stats['errors'] > 0:
            print(f"   ⚠️  Errors: {stats['errors']}")

        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Google Drive documents")
    parser.add_argument(
        "--folders",
        type=str,
        required=True,
        help="Comma-separated list of Google Drive folder IDs",
    )

    args = parser.parse_args()

    folder_id_list = [fid.strip() for fid in args.folders.split(",") if fid.strip()]

    if not folder_id_list:
        print("❌ Error: No folder IDs provided", file=sys.stderr)
        sys.exit(1)

    exit_code = asyncio.run(main(folder_ids=folder_id_list))
    sys.exit(exit_code)
