import asyncio
import itertools
import json
import logging
import re
from pathlib import Path

import pandas as pd

import config

logger = logging.getLogger(__name__)


def parse_json_file(json_file: Path):
    try:
        content = json_file.read_text(encoding="utf-8")
        data = json.loads(content)
        res_data = data[0].get("result", {}).get("data", {})
        json_data = res_data.get("json", res_data)
        items = json_data.get("items")
        if not items or not isinstance(items, list):
            raise ValueError()
        logger.info(f"Found {len(items)} items in {json_file}")
        return items
    except Exception as e:
        logger.error(
            f"Error parsing JSON file {json_file.name}: {e}", exc_info=True
        )
        raise


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
        r"results_page-(?P<page>\d+)_(?P<date>\d{4}-\d{2}-\d{2})\.json"
    )

    # Gather matching JSON files
    json_files = list(results_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} JSON files to parse in {results_dir}")

    # Parse JSON files in parallel
    tasks = [
        asyncio.to_thread(parse_json_file, json_file)
        for json_file in json_files
    ]
    logger.info("Executing parallel extraction of JSON files...")
    parsed_lists = await asyncio.gather(*tasks)

    # Group extracted items by their file's date string
    items_by_date = {}
    for json_file, items in zip(json_files, parsed_lists):
        match = pattern.match(json_file.name)
        if match:
            date_str = match.group("date")
            items_by_date.setdefault(date_str, []).extend(items)

    all_parsed_records = []

    for date_str, items in items_by_date.items():
        if not items:
            continue

        df = pd.DataFrame(items)

        # Drop duplicates by "id" to keep unique properties
        if "id" in df.columns:
            df = df.drop_duplicates(subset=["id"])
        else:
            logger.warning(
                f"No 'id' column found in items for date {date_str}. Skipping deduplication."
            )

        # Map API keys to target columns
        rename_map = {
            "region": "area",
            "publicStatus": "status",
            "propertyType": "tag",
        }
        df.drop(columns=rename_map.values(), errors="ignore", inplace=True)
        df.rename(columns=rename_map, inplace=True)

        # Standardize missing/null values as empty strings
        for col in ["area", "status", "tag"]:
            if col not in df.columns:
                df[col] = ""
            df[col] = df[col].fillna("").astype(str).str.strip()

        # Extract unique, non-empty options dynamically from the dataset
        area_opts = [x for x in df["area"].unique() if x != ""]
        status_opts = [x for x in df["status"].unique() if x != ""]
        tag_opts = [x for x in df["tag"].unique() if x != ""]

        # Append the empty string ("") representing "all" / unfiltered values
        area_opts_with_empty = area_opts + [""]
        status_opts_with_empty = status_opts + [""]
        tag_opts_with_empty = tag_opts + [""]

        # Generate all permutations
        combinations = list(
            itertools.product(
                area_opts_with_empty,
                status_opts_with_empty,
                tag_opts_with_empty,
            )
        )

        # Exclude the completely empty combination if matching old behavior
        combinations = [
            c for c in combinations if not all(item == "" for item in c)
        ]

        records = []
        for a, s, t in combinations:
            mask = pd.Series(True, index=df.index)

            # Apply filters only if a field is not empty
            if a != "":
                mask &= df["area"] == a
            if s != "":
                mask &= df["status"] == s
            if t != "":
                mask &= df["tag"] == t

            count = int(mask.sum())
            records.append(
                {
                    "ts": date_str,
                    "area": a,
                    "status": s,
                    "tag": t,
                    "count": count,
                }
            )

        if records:
            all_parsed_records.append(pd.DataFrame(records))

    if not all_parsed_records:
        logger.info(
            "No valid records were found to process. Exiting extraction."
        )
        return

    # Merge counts from all parsed dates
    new_df = pd.concat(all_parsed_records, ignore_index=True)

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
