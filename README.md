# Code Reviewer

Code Reviewer is a command-line tool that uses AI to review your code changes. The tool reviews each file in your diff and provides a summary of the changes. The summary is saved to a file called `code_review_summary.md`.

## Installation

This project uses uv to manage dependencies. Install it with:

```bash
uv sync
```

## Usage
### Run locally without installing

```bash
uv run code-reviewer review
```

### Install locally as CLI

Until I've packed this properly, you can do:
```bash
uv tool install .
```

Now you can run:
```bash
code-reviewer review
```

## Options

Review staged changes:
```bash
code-reviewer review --staged
```

Review changes compared to a specific branch:
```bash
code-reviewer review --compare-to main
```

