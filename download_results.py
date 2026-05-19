import asyncio
import itertools
import json
import logging
from pathlib import Path

from curl_cffi import requests

import config
from utils import get_tokyo_datetime

logger = logging.getLogger(__name__)


# --- fetch_and_save remains the same as your original logic ---
async def fetch_and_save(session, sem, combo):
    area, status, tag = combo

    # Build query string
    query = "s=&st_cs_ttl_only="
    for field in combo:
        field_name = field[1]
        field_value = field[2]
        if field_name and field_value:
            query += f"&{field_name}={field_value}"
    query += "&st_cs_op=and&st_cs=1"

    url = f"https://zero.estate/?{query}"

    area_name = area[0] if area[0] is not None else "None"
    status_name = status[0] if status[0] is not None else "None"
    tag_name = tag[0] if tag[0] is not None else "None"
    ts = get_tokyo_datetime().date()

    file_name = f"results_area-{area_name}_status-{status_name}_tag-{tag_name}_{ts}.html"
    file_path = Path(config.DOWNLOADED_DIR) / file_name

    async with sem:
        try:
            logger.info(f"Fetching URL: {url}")
            response = await session.get(url, timeout=30)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(response.text, encoding="utf-8")
            logger.info(f"Successfully downloaded and saved: {file_name}")
        except Exception as e:
            logger.info(f"Error fetching {file_name}: {e}", exc_info=True)


async def download_results():
    file_name = "results.html"
    options_path = Path(config.CONVERTED_DIR) / Path(
        config.FILES[file_name]["options_json"]
    )

    logger.info(f"Reading options from {options_path}")
    with options_path.open("r", encoding="utf-8") as f:
        options: dict = json.load(f)

    # We define "anchors": unique strings we know exist in specific categories.
    area_anchors = ["北海道", "関東", "近畿", "甲信越", "四国"]
    status_anchors = ["募集中", "成約済", "受付停止"]
    tag_anchors = ["アパート", "マンション", "土地", "建物"]

    # Helper function to find the top-level key matching any anchor
    def find_category_key(options_dict, anchors):
        for key, sub_dict in options_dict.items():
            # Check if any anchor string exists as a sub-key within the dictionary
            if any(anchor in sub_dict for anchor in anchors):
                return key
        return None

    area_key = find_category_key(options, area_anchors)
    status_key = find_category_key(options, status_anchors)
    tag_key = find_category_key(options, tag_anchors)

    if not all([area_key, status_key, tag_key]):
        raise ValueError(
            f"Could not identify category keys. Found: Area={area_key}, Status={status_key}, Tag={tag_key}"
        )

    logger.info(
        f"Identified Keys -> Area: {area_key}, Status: {status_key}, Tag: {tag_key}"
    )

    # Helper function to extract (Label, Field, Value)
    def get_list_for(key):
        empty_choice = (None, None, None)
        data = options[key]
        return [(label, v["name"], v["value"]) for label, v in data.items()] + [
            empty_choice
        ]

    # Force the lists into a specific order: Area, Status, Tag
    # This ensures 'combo' in fetch_and_save always has the correct index mapping.
    area_opts = get_list_for(area_key)
    status_opts = get_list_for(status_key)
    tag_opts = get_list_for(tag_key)

    # Generate all combinations
    combinations = list(itertools.product(area_opts, status_opts, tag_opts))

    # Remove the combination where all three are blank
    combinations = [
        c for c in combinations if not all(item[0] is None for item in c)
    ]

    logger.info(
        f"Loaded options successfully. Total permutations: {len(combinations)}"
    )

    sem = asyncio.Semaphore(10)
    logger.info("Starting concurrent downloads...")
    async with requests.AsyncSession() as session:
        tasks = [fetch_and_save(session, sem, combo) for combo in combinations]
        await asyncio.gather(*tasks)

    logger.info("All downloads completed successfully!")


if __name__ == "__main__":
    asyncio.run(download_results())
