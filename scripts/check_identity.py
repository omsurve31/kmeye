"""Pre-commit guard: neutral git identity and no blocked personal strings in staged files.

The blocked strings (real name, email, handles) live in an untracked `.identity-blocklist` file,
one per line, so they never enter the repository. See `.identity-blocklist.example`.
"""

import subprocess
import sys
from pathlib import Path

EXPECTED_EMAIL = "anon@example.com"
BLOCKLIST_PATH = Path(".identity-blocklist")


def run_git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return result.stdout


def read_blocked_strings() -> list[str]:
    if not BLOCKLIST_PATH.exists():
        return []
    lines = BLOCKLIST_PATH.read_text(encoding="utf-8").splitlines()
    return [line.strip().lower() for line in lines if line.strip() and not line.startswith("#")]


def find_problems() -> list[str]:
    problems = []
    email = run_git("config", "user.email").strip()
    if email != EXPECTED_EMAIL:
        problems.append(f"git user.email is '{email}', expected '{EXPECTED_EMAIL}'")
    blocked_strings = read_blocked_strings()
    staged_files = run_git("diff", "--cached", "--name-only", "--diff-filter=ACM").splitlines()
    for file_name in staged_files:
        text = Path(file_name).read_bytes().decode("utf-8", errors="ignore").lower()
        for blocked_string in blocked_strings:
            if blocked_string in text:
                problems.append(f"{file_name} contains a blocked string")
    return problems


def main() -> int:
    problems = find_problems()
    for problem in problems:
        print(f"identity check failed: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
