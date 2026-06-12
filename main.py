import asyncio

from download_results import download_results
from extract_results import extract_results


async def main():
    await download_results()
    await extract_results()


if __name__ == "__main__":
    asyncio.run(main())
