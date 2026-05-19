"""
Simon the Verifier — GitHub Actions verification script.

Reads changed files from the current push, sends them to the GitHub Models API
using Simon-the-verifier's checklist, and writes a Markdown report to the
GitHub Actions job summary ($GITHUB_STEP_SUMMARY).
"""

import os
import sys
from pathlib import Path

from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
COMMIT_SHA = os.environ.get("COMMIT_SHA", "unknown")
COMMIT_MESSAGE = os.environ.get("COMMIT_MESSAGE", "(no message)")
PUSHER = os.environ.get("PUSHER", "unknown")
REPO = os.environ.get("REPO", "unknown")
REF = os.environ.get("REF", "unknown")
STEP_SUMMARY = os.environ.get("GITHUB_STEP_SUMMARY", "summary.md")

# Limit per-file content sent to the model to avoid token overflows
MAX_FILE_CHARS = 4000
# Maximum total content characters across all files
MAX_TOTAL_CHARS = 20000

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN,
)


def read_changed_files() -> list[dict]:
    """Return a list of {path, content} dicts for every changed file."""
    changed: list[dict] = []
    changed_files_path = Path("changed_files.txt")
    if not changed_files_path.exists():
        return changed

    total_chars = 0
    with open(changed_files_path) as f:
        for line in f:
            filepath = line.strip()
            if not filepath:
                continue
            p = Path(filepath)
            if p.exists() and p.is_file():
                try:
                    raw = p.read_text(encoding="utf-8", errors="replace")
                    truncated = raw[:MAX_FILE_CHARS]
                    if len(raw) > MAX_FILE_CHARS:
                        truncated += f"\n... [truncated — {len(raw)} total chars]"
                    total_chars += len(truncated)
                    changed.append({"path": filepath, "content": truncated})
                except Exception as exc:
                    changed.append({"path": filepath, "content": f"[Could not read: {exc}]"})
            else:
                changed.append({"path": filepath, "content": "[File deleted or not found in working tree]"})

            if total_chars >= MAX_TOTAL_CHARS:
                changed.append(
                    {"path": "...", "content": f"[Further files omitted — total content limit of {MAX_TOTAL_CHARS} chars reached]"}
                )
                break

    return changed


def build_prompt(files: list[dict]) -> str:
    files_section = ""
    for f in files:
        lang = Path(f["path"]).suffix.lstrip(".") or "text"
        files_section += f"\n### `{f['path']}`\n```{lang}\n{f['content']}\n```\n"

    return f"""You are Simon the Verifier, a rigorous code review agent.

A push was made to **{REPO}** on `{REF}` by **{PUSHER}**.
Commit: `{COMMIT_SHA[:8]}` — "{COMMIT_MESSAGE}"

Changed files in this push:
{files_section}

Perform a structured verification report covering all six points below.
Be concise but thorough. Use bullet points inside each section.

1. **Task Clarity** — Is the intent of the change clearly defined and understood from the commit message and code?
2. **Resources & Information** — Are all necessary dependencies, imports, or external resources present and correct?
3. **Step-by-Step Plan** — Does the code follow a logical, well-structured approach to the task?
4. **Potential Challenges & Solutions** — Identify any edge cases, security concerns (OWASP Top 10), or fragile assumptions.
5. **Accuracy & Completeness** — Is the implementation correct? Are there TODO stubs, dead code, or missing pieces?
6. **Exception Handling** — Is there sufficient error handling for foreseeable failures?

End with an **Overall Verdict** line in bold:
- ✅ **PASS** — ready to merge
- ⚠️ **NEEDS ATTENTION** — minor issues to address
- ❌ **FAIL** — significant problems found

Format everything as clean GitHub-flavoured Markdown."""


def write_summary(report: str) -> None:
    short_sha = COMMIT_SHA[:8] if len(COMMIT_SHA) >= 8 else COMMIT_SHA
    header = f"""# Simon the Verifier Report

| Field | Value |
|---|---|
| **Commit** | `{short_sha}` |
| **Message** | {COMMIT_MESSAGE} |
| **Pushed by** | {PUSHER} |
| **Ref** | `{REF}` |
| **Repository** | {REPO} |

---

"""
    with open(STEP_SUMMARY, "a", encoding="utf-8") as fh:
        fh.write(header + report + "\n")


def main() -> None:
    files = read_changed_files()

    if not files:
        report = "_No source files were changed in this push — nothing to verify._"
        write_summary(report)
        print("No files to verify.")
        return

    print(f"Verifying {len(files)} changed file(s)...")
    prompt = build_prompt(files)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Simon the Verifier. Your sole purpose is to review code changes "
                        "and produce structured verification reports. Be precise and actionable."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        report = response.choices[0].message.content or "(empty response from model)"
    except Exception as exc:
        report = (
            f"**Error — verification model could not be reached.**\n\n"
            f"```\n{exc}\n```\n\n"
            "_Please check that the repository has access to GitHub Models and that `GITHUB_TOKEN` has the required permissions._"
        )
        write_summary(report)
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    write_summary(report)
    print("Verification complete. Report written to job summary.")


if __name__ == "__main__":
    main()
