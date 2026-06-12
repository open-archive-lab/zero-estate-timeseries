import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s: %(message)s"
)

DOWNLOADED_DIR = "downloaded"
CONVERTED_DIR = "converted"

FILES = {
    "results.json": {
        "url": "https://zero.estate/api/trpc/property.list",
        "limit": 100,
    },
    "results.csv": {},
}
