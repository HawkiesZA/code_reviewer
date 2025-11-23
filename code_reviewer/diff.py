import subprocess
import re
from typing import List, Dict


def run_git(args: List[str]) -> str:
    return subprocess.check_output(args, text=True).strip()


def get_diff(staged: bool = False) -> str:
    cmd = ["git", "diff", "--patch"]
    if staged:
        cmd.append("--cached")
    return run_git(cmd)

def detect_upstream_base() -> str | None:
    """
    Returns the upstream tracking branch name if one exists,
    otherwise returns None.
    """
    try:
        upstream = run_git(["git", "rev-parse", "--abbrev-ref", "@{upstream}"])
        return upstream
    except subprocess.CalledProcessError:
        return None

def detect_main_or_master() -> str:
    """
    Fallback branch detection if upstream not set.
    Prefer 'main', then 'master', else origin/main.
    """
    branches = run_git(["git", "branch", "--format=%(refname:short)"]).splitlines()
    remotes = run_git(["git", "branch", "-r", "--format=%(refname:short)"]).splitlines()

    if "main" in branches:
        return "main"
    if "master" in branches:
        return "master"
    if "origin/main" in remotes:
        return "origin/main"
    if "origin/master" in remotes:
        return "origin/master"

    # Final fallback
    return "main"

def get_pr_diff(compare_to: str | None = None) -> str:
    """
    Get diff for a PR branch by comparing current HEAD to a base branch.
    Priority:
      1. Explicit --compare-to flag
      2. Upstream branch
      3. main/master auto-detect
    """

    # 1. User explicitly specified base branch
    if compare_to:
        return run_git(["git", "diff", f"{compare_to}...HEAD"])

    # 2. Try upstream
    upstream = detect_upstream_base()
    if upstream:
        try:
            return run_git(["git", "diff", f"{upstream}...HEAD"])
        except subprocess.CalledProcessError:
            pass  # graceful fallback

    # 3. Fallback to main/master detection
    fallback = detect_main_or_master()
    return run_git(["git", "diff", f"{fallback}...HEAD"])


def split_by_file(diff_text: str) -> Dict[str, str]:
    """
    Split diff output into separate files.
    """
    files = {}
    current_file = None
    current_diff: list[str] = []

    for line in diff_text.splitlines(True):
        if line.startswith("diff --git"):
            if current_file and current_diff:
                files[current_file] = "".join(current_diff)
            current_diff = []
            # extract filename (right side)
            parts = line.strip().split(" ")
            current_file = parts[-1][2:]  # strip b/
        current_diff.append(line)

    if current_file and current_diff:
        files[current_file] = "".join(current_diff)

    return files


def split_into_hunks(diff_text: str) -> List[str]:
    """
    Split a file diff into individual hunks.
    """
    hunks = re.split(r"(?=^@@ )", diff_text, flags=re.MULTILINE)
    return [h for h in hunks if "@@" in h]