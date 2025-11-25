import os
import click
import asyncio
import functools
from .diff import get_pr_diff, get_diff
from .agents import ReviewAgent, summarise_reviews
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
@click.option(
    "--output-file",
    default="code_review_summary.md",
    help="Output file for the review summary (default: code_review_summary.md)."
)
@click.option(
    "--token-limit",
    default=5000,
    type=int,
    help="Maximum tokens to process in one go (default: 5000)."
)
@make_sync
async def review(staged, compare_to, output_file, token_limit):
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

    # calculate token size of diff by getting total characters and dividing by 5 (approximate token count)
    total_chars = len(diff_text)
    estimated_tokens = total_chars // 5
    logger.info(f"Estimated tokens in diff: {estimated_tokens}")
    logger.info(f"Token limit: {token_limit}")

    review_agent = ReviewAgent()
    final_review = ""
    # if the estimated token count is small enough, we can review the whole diff at once
    if estimated_tokens < token_limit:
        logger.info("Diff is small enough to review in one go.")
        final_review = await review_agent.review(diff_text)
    else:
        logger.info("Diff is too large, reviewing files individually.")

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
                review = await review_agent.review(hunk)
                logger.info(review)
                reviews.append(review)

        # Summarise reviews
        logger.info("\n=== 📄 Summary ===")
        final_review = await summarise_reviews(reviews)
        logger.info(final_review)

    with open(output_file, "w") as f:
        f.write(final_review)
    
    print(f"\n=== 📄 Review saved to {output_file} ===")