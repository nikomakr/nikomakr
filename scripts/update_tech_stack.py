"""
Auto-detects languages across all public GitHub repos
and updates the Tech Stack section in README.md
"""

import os
import re
import requests

# ── Config ────────────────────────────────────────────────────────────────────

USERNAME = os.environ.get("GITHUB_USERNAME", "nikomakr")
TOKEN    = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

# ── Language → badge mapping ───────────────────────────────────────────────────
# Add more here if you ever pick up a new language!

BADGE_MAP = {
    # Languages
    "Java":        "![Java](https://img.shields.io/badge/Java-%23ED8B00.svg?style=for-the-badge&logo=openjdk&logoColor=white)",
    "JavaScript":  "![JavaScript](https://img.shields.io/badge/JavaScript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E)",
    "TypeScript":  "![TypeScript](https://img.shields.io/badge/TypeScript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white)",
    "Python":      "![Python](https://img.shields.io/badge/Python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)",
    "Go":          "![Go](https://img.shields.io/badge/Go-%2300ADD8.svg?style=for-the-badge&logo=go&logoColor=white)",
    "C":           "![C](https://img.shields.io/badge/C-%2300599C.svg?style=for-the-badge&logo=c&logoColor=white)",
    "C++":         "![C++](https://img.shields.io/badge/C++-%2300599C.svg?style=for-the-badge&logo=c%2B%2B&logoColor=white)",
    "C#":          "![C#](https://img.shields.io/badge/C%23-%23239120.svg?style=for-the-badge&logo=csharp&logoColor=white)",
    "Rust":        "![Rust](https://img.shields.io/badge/Rust-%23000000.svg?style=for-the-badge&logo=rust&logoColor=white)",
    "Shell":       "![Bash](https://img.shields.io/badge/Bash-%23121011.svg?style=for-the-badge&logo=gnu-bash&logoColor=white)",
    "HTML":        "![HTML5](https://img.shields.io/badge/HTML5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white)",
    "CSS":         "![CSS3](https://img.shields.io/badge/CSS3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white)",
    "Kotlin":      "![Kotlin](https://img.shields.io/badge/Kotlin-%237F52FF.svg?style=for-the-badge&logo=kotlin&logoColor=white)",
    "Swift":       "![Swift](https://img.shields.io/badge/Swift-F54A2A?style=for-the-badge&logo=swift&logoColor=white)",
    "Ruby":        "![Ruby](https://img.shields.io/badge/Ruby-%23CC342D.svg?style=for-the-badge&logo=ruby&logoColor=white)",
    "PHP":         "![PHP](https://img.shields.io/badge/PHP-%23777BB4.svg?style=for-the-badge&logo=php&logoColor=white)",
    "Scala":       "![Scala](https://img.shields.io/badge/Scala-%23DC322F.svg?style=for-the-badge&logo=scala&logoColor=white)",
    "Dockerfile":  "![Docker](https://img.shields.io/badge/Docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)",
}

# Languages to skip (noise / not real tech stack items)
SKIP_LANGUAGES = {"Makefile", "Markdown", "Text", "YAML", "JSON", "TOML", "XML"}

# Minimum bytes threshold — languages below this % are ignored
MIN_PERCENT = 0.5


# ── GitHub API helpers ─────────────────────────────────────────────────────────

def get_all_repos():
    """Fetch all public repos for the user (handles pagination)."""
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}&type=owner"
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos


def get_repo_languages(repo_name):
    """Fetch language byte counts for a single repo."""
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/languages"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json()
    return {}


# ── Core logic ────────────────────────────────────────────────────────────────

def detect_languages():
    """Aggregate language bytes across all repos, return sorted list."""
    print(f"🔍 Fetching repos for {USERNAME}...")
    repos = get_all_repos()
    print(f"   Found {len(repos)} repos")

    totals = {}
    for repo in repos:
        if repo.get("fork"):          # Skip forked repos
            continue
        langs = get_repo_languages(repo["name"])
        for lang, bytes_count in langs.items():
            if lang not in SKIP_LANGUAGES:
                totals[lang] = totals.get(lang, 0) + bytes_count

    if not totals:
        print("⚠️  No languages detected.")
        return []

    total_bytes = sum(totals.values())
    # Filter by minimum percentage and sort descending
    filtered = {
        lang: count for lang, count in totals.items()
        if (count / total_bytes * 100) >= MIN_PERCENT
    }
    sorted_langs = sorted(filtered, key=filtered.get, reverse=True)

    print(f"✅ Detected languages: {sorted_langs}")
    return sorted_langs


def build_tech_stack_section(languages):
    """Build the markdown block to inject into README."""
    known   = [l for l in languages if l in BADGE_MAP]
    unknown = [l for l in languages if l not in BADGE_MAP]

    badges = "\n".join(BADGE_MAP[l] for l in known)

    note = ""
    if unknown:
        note = f"\n<!-- Also detected (no badge yet): {', '.join(unknown)} -->"

    section = f"""<!-- TECH-STACK-START -->
## 🛠️ Tech Stack
> Auto-detected from my repositories

{badges}{note}

<!-- TECH-STACK-END -->"""
    return section


def update_readme(new_section):
    """Replace the tech stack block in README.md."""
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"<!-- TECH-STACK-START -->.*?<!-- TECH-STACK-END -->"

    if re.search(pattern, content, re.DOTALL):
        # Replace existing block
        updated = re.sub(pattern, new_section, content, flags=re.DOTALL)
        action = "updated"
    else:
        # Insert before ## 📊 GitHub Stats
        marker = "## 📊 GitHub Stats"
        if marker in content:
            updated = content.replace(marker, new_section + "\n\n---\n\n" + marker)
            action = "inserted"
        else:
            # Fallback: append at end
            updated = content + "\n\n" + new_section
            action = "appended"

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"📝 README.md tech stack section {action} successfully.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    languages   = detect_languages()
    if languages:
        section = build_tech_stack_section(languages)
        update_readme(section)
    else:
        print("Nothing to update.")
