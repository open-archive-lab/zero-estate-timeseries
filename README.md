# zero-estate-timeseries

A Python-based ETL pipeline that automatically scrapes, aggregates, and tracks time-series statistics for property listings on [zero.estate](https://zero.estate/). It dynamically fetches available search filters, queries all filter permutations, and tracks the volume of properties matching those criteria over time.

## Quick start

### Install dependencies

Install python dependencies:

```bash
pip install -r requirements.txt
```

### Run

Run the full data pipeline:

```bash
python main.py
```

### Key Outputs

- **`converted/results.csv`**: The primary database containing all extracted timeseries data, including area, status, tag, date, and property counts.
- **`converted/query_options.json`**: A JSON map of the latest extracted search filters/categories available on the site.
- **`downloaded/`**: Directory storing historically processed HTML files from search queries.

## Pipeline Overview

Orchestrated by `main.py`, the pipeline runs four distinct stages:

1. **Download Options (`download_options.py`)**: Asynchronously fetches the latest filter options HTML from the `zero.estate` query options page.

2. **Extract Options (`extract_options.py`)**: Parses the downloaded HTML using `BeautifulSoup`, extracts all available search parameters, and saves them to `query_options.json`.

3. **Download Results (`download_results.py`)**: Generates all valid permutations of the parsed search filters. It dynamically builds the query URLs and asynchronously downloads the resulting search result HTML pages to the `downloaded/` directory.

4. **Extract Results (`extract_results.py`)**: Parses the downloaded search result HTML files, uses regular expressions to calculate the exact number of matching properties for each search permutation, and upserts the new timepoints into the persistent `results.csv` database.

## Automation

This project includes a GitHub Actions workflow (`Update Database`) that automatically runs the pipeline every 6 hours. It executes the scraping process, updates the datasets, and pushes any new changes in the `converted/` directory directly to the repository.

## Configuration

Settings, target URLs, and directory file paths (`downloaded`, `converted`) can be modified within `config.py`.
