#!/usr/bin/env python3
"""Convert the original bash-based GitHub search workflow into Python.

This script mimics the behavior of `ghs-bash-script.sh` by querying the
GitHub API for repositories owned by the user, starred by the user, and
those belonging to organizations the user is a member of.  It also includes
an explicit list of hardcoded repos.

The output is a JSON payload formatted for Alfred's script filter which
includes a cache header and a list of items.  Each repository entry is
followed by action items (issues, PRs, tags, etc.).

Configuration is provided via environment variables (as Alfred normally
supplies) or command-line options.

Usage::

    ./ghs.py [--username USER] [--token TOKEN] [--cache-duration SEC] [QUERY]

The environment variables `username`, `token`, and `cacheDuration` are
honored if the corresponding command line arguments are not passed.
"""

import argparse
import json
import os
import sys
from typing import List, Tuple, Optional

# the script only needs standard library modules so it works in any Python
# environment without installing additional packages.
import urllib.request
import urllib.parse
import urllib.error




# ---------------------------------------------------------------------------
# configuration helpers
# ---------------------------------------------------------------------------

def setup_config(query: str) -> Tuple[str, str, int, str]:
    """Gather configuration from arguments and environment.

    Returns a tuple of (username, token, cache_duration, query).
    """
    username = os.environ.get("username", "")
    token = os.environ.get("token", "")
    cache_duration = int(os.environ.get("cacheDuration", "0"))
    return username, token, cache_duration, query


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def fetch_github_data(url: str, headers: dict) -> List[dict]:
    """Fetch paginated results from the Github API using urllib.

    Metadata parameters are added manually and the JSON from each page is
    appended to a list.  HTTP errors raise `urllib.error.HTTPError` which is
    handled by the caller if necessary.
    """
    results: List[dict] = []
    page = 1
    while True:
        params = urllib.parse.urlencode({"per_page": 100, "page": page})
        full_url = f"{url}?{params}"
        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
        page_data = json.loads(data)
        if not page_data:
            break
        results.extend(page_data)
        page += 1
    return results


def get_user_repos(headers: dict) -> List[Tuple[str, Optional[str], bool]]:
    raw = fetch_github_data(
        "https://api.github.com/user/repos?affiliation=owner,collaborator,organization_member",
        headers,
    )
    return [(_parse_repo(r)) for r in raw]


def get_starred_repos(headers: dict) -> List[Tuple[str, Optional[str], bool]]:
    raw = fetch_github_data("https://api.github.com/user/starred", headers)
    return [(_parse_repo(r)) for r in raw]


def get_org_repos(headers: dict, username: str) -> List[Tuple[str, Optional[str], bool]]:
    req = urllib.request.Request(f"https://api.github.com/users/{username}/orgs", headers=headers)
    with urllib.request.urlopen(req) as resp:
        orgs = json.loads(resp.read())
    all_repos: List[Tuple[str, Optional[str], bool]] = []
    for o in orgs:
        name = o.get("login")
        if not name:
            continue
        repos = fetch_github_data(f"https://api.github.com/orgs/{name}/repos", headers)
        all_repos.extend(_parse_repo(r) for r in repos)
    return all_repos


def _parse_repo(repo_json: dict) -> Tuple[str, Optional[str], bool]:
    return repo_json.get("full_name", ""), repo_json.get("description"), bool(repo_json.get("fork"))


def get_hardcoded_repos() -> List[Tuple[str, Optional[str], bool]]:
    hard = [
        ("apache/datafusion", "Apache DataFusion is a very fast, extensible query engine for building high-quality data-centric systems in Rust, using the Apache Arrow in-memory format.", False),
        ("apache/datafusion-python", "Python bindings for Apache DataFusion", False),
        ("apache/datafusion-ballista", "Apache DataFusion Ballista Distributed Query Engine", False),
        ("apache/arrow-rs", "Apache Arrow Rust implementation", False),
    ]
    return hard


def gather_all_repos(headers: dict, username: str) -> List[Tuple[str, Optional[str], bool]]:
    repos: List[Tuple[str, Optional[str], bool]] = []
    repos.extend(get_user_repos(headers))
    repos.extend(get_starred_repos(headers))
    if username:
        repos.extend(get_org_repos(headers, username))
    repos.extend(get_hardcoded_repos())
    return repos


def process_repositories(
    repos: List[Tuple[str, Optional[str], bool]]
) -> List[Tuple[str, Optional[str], bool]]:
    """Deduplicate and sort repositories.

    Repositories are unique by full name and non-forked repositories are
    listed before forks, preserving the first occurrence of each name.
    """
    seen = set()
    unique: List[Tuple[str, Optional[str], bool]] = []
    for name, desc, fork in repos:
        if name in seen or not name:
            continue
        seen.add(name)
        unique.append((name, desc, fork))

    nonfork = [r for r in unique if not r[2]]
    forked = [r for r in unique if r[2]]
    return nonfork + forked


def filter_repositories(
    repos: List[Tuple[str, Optional[str], bool]], query: str
) -> List[Tuple[str, Optional[str], bool]]:
    if not query:
        return repos
    q = query.lower()
    return [r for r in repos if q in r[0].lower() or (r[1] and q in r[1].lower())]


# ---------------------------------------------------------------------------
# Alfred JSON generation
# ---------------------------------------------------------------------------

def generate_repo_item(name: str, description: Optional[str]) -> dict:
    if not description:
        description = "No description provided"
    title_with_desc = f"{name} - {description}"
    return {
        "title": title_with_desc,
        "subtitle": description,
        "arg": f"https://github.com/{name}",
        "mods": {
            "cmd": {
                "subtitle": "⌘: Copy URL to clipboard",
                "arg": f"https://github.com/{name}",
            }
        },
    }


def generate_repo_actions(name: str, username: str) -> List[dict]:
    # returns a list of dictionaries representing the extra actions
    template: List[dict] = []
    add = template.append
    add(
        {
            "title": f"{name} Issues",
            "subtitle": "View Issues",
            "arg": f"https://github.com/{name}/issues",
            "mods": {"cmd": {"subtitle": "⌘: Copy Issues URL to clipboard", "arg": f"https://github.com/{name}/issues"}},
        }
    )
    add(
        {
            "title": f"{name} New Issue",
            "subtitle": "New Issue",
            "arg": f"https://github.com/{name}/issues/new/choose",
            "mods": {"cmd": {"subtitle": "⌘: Copy Issues URL to clipboard", "arg": f"https://github.com/{name}/issues/new/choose"}},
        }
    )
    add(
        {
            "title": f"{name} Issue Number",
            "subtitle": "View Issue number",
            "arg": f"https://github.com/{name}/issues/var:num",
            "mods": {"cmd": {"subtitle": "⌘: Copy Issues URL to clipboard", "arg": f"https://github.com/{name}/issues/var:num"}},
        }
    )
    add(
        {
            "title": f"{name} Open bugs",
            "subtitle": "View Bug Issues",
            "arg": f"https://github.com/{name}/issues?q=is%3Aopen+is%3Aissue+label%3Abug",
            "mods": {"cmd": {"subtitle": "⌘: Copy Bug Issues URL to clipboard", "arg": f"https://github.com/{name}/issues?q=is%3Aopen+is%3Aissue+label%3Abug"}},
        }
    )
    add(
        {
            "title": f"{name} PRs",
            "subtitle": "View Pull Requests",
            "arg": f"https://github.com/{name}/pulls",
            "mods": {"cmd": {"subtitle": "⌘: Copy Pull Requests URL to clipboard", "arg": f"https://github.com/{name}/pulls"}},
        }
    )
    add(
        {
            "title": f"{name} New PR",
            "subtitle": "New Pull Request",
            "arg": f"https://github.com/{name}/compare",
            "mods": {"cmd": {"subtitle": "⌘: Copy Pull Requests URL to clipboard", "arg": f"https://github.com/{name}/compare"}},
        }
    )
    add(
        {
            "title": f"{name} PR number",
            "subtitle": "View Pull Request number",
            "arg": f"https://github.com/{name}/pull/var:num",
            "mods": {"cmd": {"subtitle": "⌘: Copy Pull Requests URL to clipboard", "arg": f"https://github.com/{name}/pulls/var:num"}},
        }
    )
    add(
        {
            "title": f"{name} Tags",
            "subtitle": "View Repository Tags",
            "arg": f"https://github.com/{name}/tags",
            "mods": {"cmd": {"subtitle": "⌘: Copy Tags URL to clipboard", "arg": f"https://github.com/{name}/tags"}},
        }
    )
    add(
        {
            "title": f"{name} Create PR",
            "subtitle": "Create a New Pull Request",
            "arg": f"https://github.com/{name}/compare/main...{username}:{name}:xxx?expand=1",
            "mods": {"cmd": {"subtitle": "⌘: Copy Create PR URL to clipboard", "arg": f"https://github.com/{name}/compare/main...{username}:{name}:xxx?expand=1"}},
        }
    )
    return template


def generate_alfred_output(
    repos: List[Tuple[str, Optional[str], bool]], cache_duration: int, username: str
) -> str:
    items: List[dict] = []
    for name, desc, fork in repos:
        items.append(generate_repo_item(name, desc))
        # always add actions for github actions
        items.append(
            {
                "title": f"{name} Actions",
                "subtitle": "View GitHub Actions",
                "arg": f"https://github.com/{name}/actions",
                "mods": {
                    "cmd": {
                        "subtitle": "⌘: Copy Actions URL to clipboard",
                        "arg": f"https://github.com/{name}/actions",
                    }
                },
            }
        )
        if not fork:
            items.extend(generate_repo_actions(name, username))

    output = {"cache": {"seconds": cache_duration, "loosereload": True}, "items": items}
    return json.dumps(output)


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="GitHub Search Alfred helper")
    parser.add_argument("query", nargs="?", default="", help="Search query")
    parser.add_argument("--username", help="GitHub username to query")
    parser.add_argument("--token", help="GitHub API token")
    parser.add_argument(
        "--cache-duration", type=int, help="Cache duration seconds for Alfred"
    )
    args = parser.parse_args()

    # environment defaults
    github_user, github_token, cache_duration_env, query_env = setup_config(args.query)
    github_username = args.username or github_user
    token = args.token or github_token
    cache_duration = args.cache_duration if args.cache_duration is not None else cache_duration_env
    query = args.query or query_env

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        all_repos = gather_all_repos(headers, github_username)
    except urllib.error.HTTPError as e:
        # GitHub returned a non-2xx response, surface the message in JSON
        print(json.dumps({"error": f"HTTPError {e.code}: {e.reason}"}))
        sys.exit(1)
    except urllib.error.URLError as e:
        # network problems (DNS, connectivity, etc.)
        print(json.dumps({"error": f"URLError: {e.reason}"}))
        sys.exit(1)

    processed = process_repositories(all_repos)
    filtered = filter_repositories(processed, query)
    print(generate_alfred_output(filtered, cache_duration, github_username))


if __name__ == "__main__":
    main()
