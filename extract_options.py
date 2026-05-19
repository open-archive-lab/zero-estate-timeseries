import asyncio
from collections import defaultdict
import json
import logging
from pathlib import Path

from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


async def extract_options():

    file_name = "query_options.json"
    file_path = Path(config.CONVERTED_DIR) / Path(file_name)

    input_file_name = config.FILES[file_name]["input"]
    input_file_path = Path(config.DOWNLOADED_DIR) / Path(input_file_name)

    logger.info(f"Reading HTML content from {input_file_path}")
    html_content = input_file_path.read_text(encoding="utf-8")

    logger.debug("Parsing HTML with BeautifulSoup")
    soup = BeautifulSoup(html_content, "html.parser")

    form = soup.find("form")
    if not form:
        logger.info(
            "Target <form> tag not found in the HTML content. Aborting extraction."
        )
        return

    result_json = defaultdict(dict)
    titles = form.find_all(class_="cs-term-title")
    logger.info(f"Found {len(titles)} term titles to process.")

    for title_tag in titles:
        section_title = title_tag.text.strip()
        associated_list = title_tag.find_next_sibling(class_="cs-term-list")

        if not associated_list:
            logger.info(
                f"No associated list found for section: {section_title}. Skipping."
            )
            continue

        items = associated_list.find_all(class_="cs-term-item")
        for item in items:
            input_tag = item.find("input")
            name_tag = item.find(class_="cs-term-name")

            if input_tag and name_tag:
                item_name = name_tag.text.strip()
                field_name = input_tag.get("name", "")
                field_value = input_tag.get("value", "")

                result_json[section_title][item_name] = {
                    "name": field_name,
                    "value": field_value,
                }

    logger.info(f"Saving extracted options to {file_path}")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2, sort_keys=True)
    logger.info("Options successfully extracted and saved.")


if __name__ == "__main__":
    asyncio.run(extract_options())
