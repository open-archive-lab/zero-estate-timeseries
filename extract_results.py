import asyncio
import logging
import re
from pathlib import Path

import pandas as pd

import config

logger = logging.getLogger(__name__)


def parse_html_file(html_file: Path, pattern: re.Pattern):
    match = pattern.match(html_file.name)
    if not match:
        logger.info(
            f"Filename {html_file.name} did not match the expected pattern. Skipping."
        )
        return None

    # Convert "None" strings back to empty strings for the CSV
    area = match.group("area") if match.group("area") != "None" else ""
    status = match.group("status") if match.group("status") != "None" else ""
    tag = match.group("tag") if match.group("tag") != "None" else ""
    date = match.group("date")

    html_content = html_file.read_text(encoding="utf-8")

    count = None
    count_match = re.search(r"検索結果\s*([\d,]+)\s*件", html_content)
    if count_match:
        count = int(count_match.group(1).replace(",", ""))

    label_parts = list(filter(None, [area, status, tag]))
    label = " | ".join(label_parts)

    if count is None:
        logger.info(
            f"Cannot find count in {html_file.name}. Label: {label}. Html content: {html_content}"
        )
        return None

    logger.info(f"Extracted data: {label} -> {count} results")

    return {
        "ts": date,
        "area": area,
        "status": status,
        "tag": tag,
        "count": count,
    }


async def extract_results():
    file_name = "results.csv"
    file_path = Path(config.CONVERTED_DIR) / Path(file_name)
    results_dir = Path(config.DOWNLOADED_DIR)

    if not results_dir.exists():
        logger.info(
            f"Directory {results_dir} does not exist. Cannot extract results."
        )
        return

    pattern = re.compile(
        r"results_area-(?P<area>.*?)_status-(?P<status>.*?)_tag-(?P<tag>.*?)_(?P<date>\d{4}-\d{2}-\d{2})\.html"
    )

    # Find all HTML files to process
    html_files = list(results_dir.glob("*.html"))
    logger.info(f"Found {len(html_files)} HTML files to parse in {results_dir}")

    tasks = [
        asyncio.to_thread(parse_html_file, html_file, pattern)
        for html_file in html_files
    ]

    logger.info("Executing parallel extraction...")
    parsed_outputs = await asyncio.gather(*tasks)

    valid_results = [r for r in parsed_outputs if r is not None]

    if not valid_results:
        logger.info(
            "No valid results were found to process. Exiting extraction."
        )
        return

    logger.info(f"Successfully parsed {len(valid_results)} valid records.")
    new_df = pd.DataFrame(valid_results)

    key_columns = ["ts", "area", "status", "tag"]
    new_df[key_columns] = new_df[key_columns].fillna("")
    new_df = new_df.drop_duplicates(subset=key_columns, keep="last")

    if file_path.exists():
        logger.info(
            f"Existing file found at {file_path}. Performing DataFrame upsert..."
        )
        # Keep as str to match parsed empty strings safely
        existing_df = pd.read_csv(file_path, dtype=str)
        existing_df[key_columns] = existing_df[key_columns].fillna("")
        existing_df["count"] = pd.to_numeric(existing_df["count"])

        existing_df.set_index(key_columns, inplace=True)
        new_df.set_index(key_columns, inplace=True)
        final_df = new_df.combine_first(existing_df).reset_index()
    else:
        logger.info("No existing file found. Creating a new DataFrame...")
        final_df = new_df

    file_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(file_path, index=False, encoding="utf-8")

    logger.info(
        f"Extraction pipeline complete! Master data saved to {file_path}"
    )


if __name__ == "__main__":
    asyncio.run(extract_results())
