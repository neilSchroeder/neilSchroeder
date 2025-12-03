#!/usr/bin/env python3
"""
Fetches unique repositories the user has contributed to in the last year
and updates the README with a formatted list.
"""

import os
import re
import requests
from datetime import datetime, timedelta
from collections import defaultdict

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
USERNAME = "neilSchroeder"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# Markers in README where we'll insert the contribution list
START_MARKER = "<!--START_SECTION:contributions-->"
END_MARKER = "<!--END_SECTION:contributions-->"


def get_contribution_events():
    """Fetch push events and PR events from the last year."""
    events_url = f"https://api.github.com/users/{USERNAME}/events/public"

    one_year_ago = datetime.now() - timedelta(days=365)
    repos = defaultdict(
        lambda: {
            "commits": 0,
            "prs": 0,
            "last_activity": None,
            "description": "",
            "url": "",
        }
    )

    page = 1
    while page <= 10:  # GitHub API limits to 10 pages (300 events max)
        response = requests.get(
            events_url, headers=HEADERS, params={"per_page": 30, "page": page}
        )

        if response.status_code != 200:
            print(f"Error fetching events: {response.status_code}")
            break

        events = response.json()
        if not events:
            break

        for event in events:
            event_date = datetime.strptime(event["created_at"], "%Y-%m-%dT%H:%M:%SZ")

            if event_date < one_year_ago:
                continue

            repo_name = event["repo"]["name"]
            repo_url = f"https://github.com/{repo_name}"

            if event["type"] == "PushEvent":
                commit_count = len(event.get("payload", {}).get("commits", []))
                repos[repo_name]["commits"] += commit_count
                repos[repo_name]["url"] = repo_url

            elif event["type"] == "PullRequestEvent":
                if event.get("payload", {}).get("action") in ["opened", "closed"]:
                    repos[repo_name]["prs"] += 1
                    repos[repo_name]["url"] = repo_url

            # Track most recent activity
            if (
                repos[repo_name]["last_activity"] is None
                or event_date > repos[repo_name]["last_activity"]
            ):
                repos[repo_name]["last_activity"] = event_date

        page += 1

    return repos


def get_repo_details(repo_full_name):
    """Fetch repository details like description and language."""
    repo_url = f"https://api.github.com/repos/{repo_full_name}"
    response = requests.get(repo_url, headers=HEADERS)

    if response.status_code == 200:
        data = response.json()
        return {
            "description": data.get("description", ""),
            "language": data.get("language", ""),
            "stars": data.get("stargazers_count", 0),
            "is_fork": data.get("fork", False),
        }
    return {"description": "", "language": "", "stars": 0, "is_fork": False}


def format_contributions(repos):
    """Format the contributions as a markdown section."""
    if not repos:
        return "_No recent public contributions found._"

    # Sort by most recent activity
    sorted_repos = sorted(
        repos.items(), key=lambda x: x[1]["last_activity"] or datetime.min, reverse=True
    )

    # Get details for top repos and format
    lines = []
    for repo_name, data in sorted_repos[:8]:  # Show top 8 repos
        details = get_repo_details(repo_name)

        # Format: repo name with link, language badge, brief stats
        owner, name = repo_name.split("/")

        # Create activity summary
        activity_parts = []
        if data["commits"] > 0:
            activity_parts.append(f"{data['commits']} commits")
        if data["prs"] > 0:
            activity_parts.append(f"{data['prs']} PRs")
        activity_str = ", ".join(activity_parts) if activity_parts else "activity"

        # Language emoji mapping
        lang_emoji = {
            "Python": "🐍",
            "JavaScript": "🟨",
            "TypeScript": "🔷",
            "Jupyter Notebook": "📓",
            "HTML": "🌐",
            "CSS": "🎨",
            "Shell": "🐚",
            "C++": "⚡",
            "R": "📊",
        }.get(details.get("language", ""), "📁")

        lang = details.get("language", "")
        lang_str = f" `{lang}`" if lang else ""

        # Format the line
        line = f"| {lang_emoji} | [{name}]({data['url']}) | {activity_str} |{lang_str}"
        lines.append(line)

    # Build the table
    table = "| | Repository | Activity | Language |\n"
    table += "|---|---|---|---|\n"
    table += "\n".join(lines)

    # Add timestamp
    updated = datetime.now().strftime("%B %d, %Y")
    footer = f"\n\n<sub>Last updated: {updated}</sub>"

    return table + footer


def update_readme(content):
    """Update the README file with new contribution content."""
    readme_path = "README.md"

    with open(readme_path, "r") as f:
        readme = f.read()

    # Check if markers exist
    if START_MARKER not in readme:
        print("Start marker not found in README. Please add the markers.")
        return False

    if END_MARKER not in readme:
        print("End marker not found in README. Please add the markers.")
        return False

    # Replace content between markers
    pattern = f"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}"
    replacement = f"{START_MARKER}\n{content}\n{END_MARKER}"

    new_readme = re.sub(pattern, replacement, readme, flags=re.DOTALL)

    with open(readme_path, "w") as f:
        f.write(new_readme)

    print("README updated successfully!")
    return True


def main():
    print(f"Fetching contributions for {USERNAME}...")
    repos = get_contribution_events()
    print(f"Found {len(repos)} unique repositories with contributions")

    content = format_contributions(repos)
    update_readme(content)


if __name__ == "__main__":
    main()
