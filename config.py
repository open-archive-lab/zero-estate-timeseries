import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s: %(message)s"
)

DOWNLOADED_DIR = "downloaded"
CONVERTED_DIR = "converted"

FILES = {
    "query_options.html": {"url": "https://zero.estate/category/zero/"},
    "query_options.json": {"input": "query_options.html"},
    "results.html": {
        "url": "https://zero.estate/",
        "options_json": "query_options.json",
    },
    "results.csv": {},
}
