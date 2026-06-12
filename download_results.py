import asyncio
import json
import logging
from pathlib import Path

from curl_cffi import requests

import config
from utils import get_tokyo_datetime

logger = logging.getLogger(__name__)

FILE_NAME = "results.json"
API_URL = config.FILES[FILE_NAME]["url"]
LIMIT = config.FILES[FILE_NAME]["limit"]


async def fetch_page(session, sem, page, ts):
    params = {
        "batch": "1",
        "input": json.dumps({"0": {"json": {"page": page, "limit": LIMIT}}}),
    }
    file_name = f"results_page-{page}_{ts}.json"
    file_path = Path(config.DOWNLOADED_DIR) / file_name

    async with sem:
        try:
            logger.info(f"Fetching API page {page}...")
            response = await session.get(API_URL, params=params, timeout=30)
            response.raise_for_status()

            # Ensure the response is valid JSON
            data = response.json()

            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info(f"Successfully downloaded and saved: {file_name}")
            return data
        except Exception as e:
            logger.error(f"Error fetching page {page}: {e}", exc_info=True)
            raise


async def download_results():
    ts = get_tokyo_datetime().date()
    sem = asyncio.Semaphore(5)

    logger.info("Starting API downloads...")
    async with requests.AsyncSession(impersonate="chrome") as session:
        # Fetch page 1 first to determine totalPages
        first_page_data = await fetch_page(session, sem, page=1, ts=ts)
        if not first_page_data:
            logger.error("Failed to fetch page 1. Aborting download.")
            return

        try:
            # Extract totalPages based on tRPC structure
            total_pages = first_page_data[0]["result"]["data"]["json"][
                "totalPages"
            ]
            logger.info(
                f"Total pages to download: {total_pages} (using limit={LIMIT})"
            )
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Could not parse totalPages from page 1: {e}")
            raise

        if total_pages > 1:
            # Fetch the rest of the pages concurrently
            tasks = [
                fetch_page(session, sem, page, ts)
                for page in range(2, total_pages + 1)
            ]
            await asyncio.gather(*tasks)

    logger.info("All API downloads completed successfully!")


if __name__ == "__main__":
    asyncio.run(download_results())
