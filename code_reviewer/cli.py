import os
import click
import asyncio
import functools
from .diff import get_pr_diff, get_diff
from .agents import review_hunk, summarise_reviews
from .diff import split_by_file, split_into_hunks
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Workaround to make async functions work with click
def make_sync(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper

@click.group()
def main():
    pass


@main.command()
@click.option("--staged", is_flag=True, default=False, help="Review staged changes only.")
@click.option(
    "--compare-to",
    default=None,
    help="Branch to compare the current branch against (default: auto-detect)."
)
@make_sync
async def review(staged, compare_to):
    """Review changed files in your Git repository."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set")

    print("🔍 Gathering diffs...")
    if compare_to:
        print(f"Comparing to {compare_to}")
        diff_text = get_pr_diff(compare_to)
    else:
        diff_text = get_diff(staged=staged)

    if not diff_text.strip():
        print("No changes detected.")
        return

    files = split_by_file(diff_text)

    # Review each file
    reviews = []
    for filename, diff in files.items():
        logger.info(f"\n=== 📄 File: {filename} ===")
        hunks = split_into_hunks(diff)

        for idx, hunk in enumerate(hunks, 1):
            logger.info(f"\n--- Hunk {idx} ---")
            logger.info(hunk)

            logger.info("\n--- AI Review ---")
            review = await review_hunk(hunk)
            logger.info(review)
            reviews.append(review)

    # Summarise reviews
    logger.info("\n=== 📄 Summary ===")
    summary = await summarise_reviews(reviews)
    logger.info(summary)
    
    # Save summary to file
    with open("code_review_summary.md", "w") as f:
        f.write(summary)
    
    print("\n=== 📄 Summary saved to code_review_summary.md ===")