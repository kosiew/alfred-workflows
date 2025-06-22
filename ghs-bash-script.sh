#!/bin/bash

# Fetch workflow configuration variables
GITHUB_USERNAME="$username"
GITHUB_TOKEN="$token"
CACHE_DURATION="$cacheDuration"
QUERY="$1"

# Headers
HEADERS=(
  -H "Accept: application/vnd.github+json"
  -H "Authorization: Bearer $GITHUB_TOKEN"
  -H "X-GitHub-Api-Version: 2022-11-28"
)

# Function to fetch paginated data from GitHub API
fetch_github_data() {
  local url="$1"
  local data=""
  local page=1
  while true; do
    local response=$(curl -s "${HEADERS[@]}" "$url?per_page=100&page=$page")
    local page_data=$(echo "$response" | jq -r '.[] | "\(.full_name)|\(.description)|\(.fork)"')
    if [[ -z "$page_data" || "$page_data" == "null" ]]; then
      break
    fi
    data="$data"$'\n'"$page_data"
    ((page++))
  done
  echo "$data"
}

# Fetch repositories from multiple sources
# 1. User's own repositories
USER_REPOS=$(fetch_github_data "https://api.github.com/user/repos")

# 2. Starred repositories
STARRED_REPOS=$(fetch_github_data "https://api.github.com/user/starred")

# 3. Repositories where user is a collaborator (this might include the missing repo)
COLLAB_REPOS=$(fetch_github_data "https://api.github.com/user/repos?affiliation=collaborator")

# 4. Organization repositories
ORG_REPOS=""
ORGS=$(curl -s "${HEADERS[@]}" "https://api.github.com/users/$GITHUB_USERNAME/orgs" | jq -r '.[].login')
for ORG in $ORGS; do
  ORG_REPOS+=$(fetch_github_data "https://api.github.com/orgs/$ORG/repos")$'\n'
done

# Combine all repositories and remove duplicates by repo name (first field)
ALL_REPOS_RAW=$(echo -e "$USER_REPOS\n$STARRED_REPOS\n$COLLAB_REPOS\n$ORG_REPOS")

# Remove duplicates by repository name (keeping the first occurrence)
# This handles cases where a repo appears in multiple sources (user, starred, org)
ALL_REPOS_UNIQUE=$(echo "$ALL_REPOS_RAW" | awk -F'|' '!seen[$1]++' | grep -v '^$')

# Separate forked and non-forked repositories
NON_FORKED_REPOS=$(echo "$ALL_REPOS_UNIQUE" | grep -v '|true$')
FORKED_REPOS=$(echo "$ALL_REPOS_UNIQUE" | grep '|true$')

# Combine and filter repositories with non-forked first
ALL_REPOS=$(echo -e "$NON_FORKED_REPOS\n$FORKED_REPOS")
FILTERED_REPOS=$(echo "$ALL_REPOS" | grep -i "$QUERY")

# Generate Alfred JSON output
echo "{
    \"cache\": {
        \"seconds\": $CACHE_DURATION,
        \"loosereload\": true
    },
    \"items\":["

first_item=true
while IFS= read -r REPO_INFO; do
  if [ -n "$REPO_INFO" ]; then
    REPO_NAME=$(echo "$REPO_INFO" | cut -d'|' -f1)
    REPO_DESCRIPTION=$(echo "$REPO_INFO" | cut -d'|' -f2)
    IS_FORK=$(echo "$REPO_INFO" | cut -d'|' -f3)
    REPO_DESCRIPTION=${REPO_DESCRIPTION:-"No description provided"}
    TITLE_WITH_DESC="$REPO_NAME - $REPO_DESCRIPTION"
    [[ "$first_item" == true ]] && first_item=false || echo ","
    
    echo "{
      \"title\": \"$TITLE_WITH_DESC\",
      \"subtitle\": \"$REPO_DESCRIPTION\",
      \"arg\": \"https://github.com/$REPO_NAME\",
      \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy URL to clipboard\", \"arg\": \"https://github.com/$REPO_NAME\"}}
    }"
    
    if [[ "$IS_FORK" != "true" ]]; then
      echo ",
      {
        \"title\": \"$REPO_NAME Issues\",
        \"subtitle\": \"View Issues\",
        \"arg\": \"https://github.com/$REPO_NAME/issues\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Issues URL to clipboard\", \"arg\": \"https://github.com/$REPO_NAME/issues\"}}
      },
      {
        \"title\": \"$REPO_NAME New Issue\",
        \"subtitle\": \"New Issue\",
        \"arg\": \"https://github.com/$REPO_NAME/issues/new/choose\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Issues URL to clipboard\", \"arg\": \"https://github.com/$REPO_NAME/issues/new/choose\"}}
      },
      {
        \"title\": \"$REPO_NAME Issue Number\",
        \"subtitle\": \"View Issue number\",
        \"arg\": \"https://github.com/$REPO_NAME/issues/var:num\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Issues URL to clipboard\", \"arg\": \"https://github.com/$REPO_NAME/issues/var:num\"}}
      },
      {
        \"title\": \"$REPO_NAME Open bugs\",
        \"subtitle\": \"View Bug Issues\",
        \"arg\": \"https://github.com/$REPO_NAME/issues?q=is%3Aopen+is%3Aissue+label%3Abug\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Bug Issues URL to clipboard\", \"arg\": \"https://github.com/$REPO_NAME/issues?q=is%3Aopen+is%3Aissue+label%3Abug\"}}
      },
      {
        \"title\": \"$REPO_NAME PRs\",
        \"subtitle\": \"View Pull Requests\",
        \"arg\": \"https://github.com/$REPO_NAME/pulls\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Pull Requests URL to clipboard\", \"arg\": \"https://github.com/$REPO_NAME/pulls\"}}
      },
      {
        \"title\": \"$REPO_NAME New PR\",
        \"subtitle\": \"New Pull Request\",
        \"arg\": \"https://github.com/$REPO_NAME/compare\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Pull Requests URL to clipboard\", \"arg\": \"https://github.com/$REPO_NAME/compare\"}}
      },
      {
        \"title\": \"$REPO_NAME PR number\",
        \"subtitle\": \"View Pull Request number\",
        \"arg\": \"https://github.com/$REPO_NAME/pulls/var:num\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Pull Requests URL to clipboard\", \"arg\": \"https://github.com/$REPO_NAME/pulls/var:num\"}}
      },
      {
        \"title\": \"$REPO_NAME Tags\",
        \"subtitle\": \"View Repository Tags\",
        \"arg\": \"https://github.com/$REPO_NAME/tags\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Tags URL to clipboard\", \"arg\": \"https://github.com/$REPO_NAME/tags\"}}
      },
      {
        \"title\": \"$REPO_NAME Create PR\",
        \"subtitle\": \"Create a New Pull Request\",
        \"arg\": \"https://github.com/$REPO_NAME/compare/main...$GITHUB_USERNAME:$REPO_NAME:xxx?expand=1\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Create PR URL to clipboard\", \"arg\": \"https://github.com/$REPO_NAME/compare/main...$GITHUB_USERNAME:$REPO_NAME:xxx?expand=1\"}}
      }"
    fi
  fi
done <<< "$FILTERED_REPOS"

echo "]}"
