import asyncio
import logging
from pathlib import Path

from curl_cffi import AsyncSession

import config

logger = logging.getLogger(__name__)


async def download_options():

    file_name = "query_options.html"
    url = config.FILES[file_name]["url"]

    logger.info(f"Starting download for {file_name} from {url}")

    async with AsyncSession() as session:
        response = await session.get(url)
        file_path = Path(config.DOWNLOADED_DIR) / Path(file_name)

        logger.debug(
            f"Creating directory structure for {file_path.parent} if it doesn't exist."
        )
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(response.text, encoding="utf-8")
        logger.info(f"Successfully saved {file_name} to {file_path}")


if __name__ == "__main__":
    asyncio.run(download_options())
