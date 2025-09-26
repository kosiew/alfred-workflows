#!/bin/bash

# Initialize configuration variables and headers
setup_config() {
  GITHUB_USERNAME="$username"
  GITHUB_TOKEN="$token"
  CACHE_DURATION="$cacheDuration"
  QUERY="$1"

  # Headers for GitHub API requests
  HEADERS=(
    -H "Accept: application/vnd.github+json"
    -H "Authorization: Bearer $GITHUB_TOKEN"
    -H "X-GitHub-Api-Version: 2022-11-28"
  )
}

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

# Fetch user repositories (owned, collaborator, organization_member)
get_user_repos() {
  fetch_github_data "https://api.github.com/user/repos?affiliation=owner,collaborator,organization_member"
}

# Fetch starred repositories
get_starred_repos() {
  fetch_github_data "https://api.github.com/user/starred"
}

# Fetch organization repositories
get_org_repos() {
  local org_repos=""
  local orgs=$(curl -s "${HEADERS[@]}" "https://api.github.com/users/$GITHUB_USERNAME/orgs" | jq -r '.[].login')
  for org in $orgs; do
    org_repos+=$(fetch_github_data "https://api.github.com/orgs/$org/repos")$'\n'
  done
  echo "$org_repos"
}

# Get hardcoded repositories that should always be included
get_hardcoded_repos() {
  cat << 'EOF'
apache/datafusion|Apache DataFusion is a very fast, extensible query engine for building high-quality data-centric systems in Rust, using the Apache Arrow in-memory format.|false
apache/datafusion-python|Python bindings for Apache DataFusion|false
apache/datafusion-ballista|Apache DataFusion Ballista Distributed Query Engine|false
apache/arrow-rs|Apache Arrow Rust implementation|false
EOF
}

# Gather all repositories from different sources
gather_all_repos() {
  local user_repos=$(get_user_repos)
  local starred_repos=$(get_starred_repos)
  local org_repos=$(get_org_repos)
  local hardcoded_repos=$(get_hardcoded_repos)
  
  echo -e "$user_repos\n$starred_repos\n$org_repos\n$hardcoded_repos"
}

# Remove duplicates and sort repositories (non-forked first)
process_repositories() {
  local all_repos_raw="$1"
  
  # Remove duplicates by repository name (keeping the first occurrence)
  local all_repos_unique=$(echo "$all_repos_raw" | awk -F'|' '!seen[$1]++' | grep -v '^$')
  
  # Separate forked and non-forked repositories
  local non_forked_repos=$(echo "$all_repos_unique" | grep -v '|true$')
  local forked_repos=$(echo "$all_repos_unique" | grep '|true$')
  
  # Combine with non-forked first
  echo -e "$non_forked_repos\n$forked_repos"
}

# Filter repositories based on query
filter_repositories() {
  local all_repos="$1"
  local query="$2"
  echo "$all_repos" | grep -i "$query"
}

# Generate Alfred JSON header
generate_alfred_header() {
  local cache_duration="$1"
  echo "{
    \"cache\": {
        \"seconds\": $cache_duration,
        \"loosereload\": true
    },
    \"items\":["
}

# Generate Alfred JSON footer
generate_alfred_footer() {
  echo "]}"
}

# Generate Alfred JSON item for a repository
generate_repo_item() {
  local repo_name="$1"
  local repo_description="$2"
  local is_first_item="$3"
  
  repo_description=${repo_description:-"No description provided"}
  local title_with_desc="$repo_name - $repo_description"
  
  [[ "$is_first_item" == "true" ]] || echo ","
  
  echo "{
      \"title\": \"$title_with_desc\",
      \"subtitle\": \"$repo_description\",
      \"arg\": \"https://github.com/$repo_name\",
      \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy URL to clipboard\", \"arg\": \"https://github.com/$repo_name\"}}
    }"
}

# Generate Alfred JSON items for non-fork repository actions
generate_repo_actions() {
  local repo_name="$1"
  
  echo ",
      {
        \"title\": \"$repo_name Issues\",
        \"subtitle\": \"View Issues\",
        \"arg\": \"https://github.com/$repo_name/issues\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Issues URL to clipboard\", \"arg\": \"https://github.com/$repo_name/issues\"}}
      },
      {
        \"title\": \"$repo_name New Issue\",
        \"subtitle\": \"New Issue\",
        \"arg\": \"https://github.com/$repo_name/issues/new/choose\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Issues URL to clipboard\", \"arg\": \"https://github.com/$repo_name/issues/new/choose\"}}
      },
      {
        \"title\": \"$repo_name Issue Number\",
        \"subtitle\": \"View Issue number\",
        \"arg\": \"https://github.com/$repo_name/issues/var:num\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Issues URL to clipboard\", \"arg\": \"https://github.com/$repo_name/issues/var:num\"}}
      },
      {
        \"title\": \"$repo_name Open bugs\",
        \"subtitle\": \"View Bug Issues\",
        \"arg\": \"https://github.com/$repo_name/issues?q=is%3Aopen+is%3Aissue+label%3Abug\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Bug Issues URL to clipboard\", \"arg\": \"https://github.com/$repo_name/issues?q=is%3Aopen+is%3Aissue+label%3Abug\"}}
      },
      {
        \"title\": \"$repo_name PRs\",
        \"subtitle\": \"View Pull Requests\",
        \"arg\": \"https://github.com/$repo_name/pulls\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Pull Requests URL to clipboard\", \"arg\": \"https://github.com/$repo_name/pulls\"}}
      },
      {
        \"title\": \"$repo_name New PR\",
        \"subtitle\": \"New Pull Request\",
        \"arg\": \"https://github.com/$repo_name/compare\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Pull Requests URL to clipboard\", \"arg\": \"https://github.com/$repo_name/compare\"}}
      },
      {
        \"title\": \"$repo_name PR number\",
        \"subtitle\": \"View Pull Request number\",
        \"arg\": \"https://github.com/$repo_name/pull/var:num\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Pull Requests URL to clipboard\", \"arg\": \"https://github.com/$repo_name/pulls/var:num\"}}
      },
      {
        \"title\": \"$repo_name Tags\",
        \"subtitle\": \"View Repository Tags\",
        \"arg\": \"https://github.com/$repo_name/tags\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Tags URL to clipboard\", \"arg\": \"https://github.com/$repo_name/tags\"}}
      },
      {
        \"title\": \"$repo_name Actions\",
        \"subtitle\": \"View GitHub Actions\",
        \"arg\": \"https://github.com/$repo_name/actions\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Actions URL to clipboard\", \"arg\": \"https://github.com/$repo_name/actions\"}}
      },
      {
        \"title\": \"$repo_name Create PR\",
        \"subtitle\": \"Create a New Pull Request\",
        \"arg\": \"https://github.com/$repo_name/compare/main...$GITHUB_USERNAME:$repo_name:xxx?expand=1\",
        \"mods\": {\"cmd\": {\"subtitle\": \"⌘: Copy Create PR URL to clipboard\", \"arg\": \"https://github.com/$repo_name/compare/main...$GITHUB_USERNAME:$repo_name:xxx?expand=1\"}}
      }"
}

# Generate Alfred JSON output for all repositories
generate_alfred_output() {
  local filtered_repos="$1"
  local cache_duration="$2"
  
  generate_alfred_header "$cache_duration"
  
  local first_item=true
  while IFS= read -r repo_info; do
    if [ -n "$repo_info" ]; then
      local repo_name=$(echo "$repo_info" | cut -d'|' -f1)
      local repo_description=$(echo "$repo_info" | cut -d'|' -f2)
      local is_fork=$(echo "$repo_info" | cut -d'|' -f3)
      
      generate_repo_item "$repo_name" "$repo_description" "$first_item"
      first_item=false
      
      if [[ "$is_fork" != "true" ]]; then
        generate_repo_actions "$repo_name"
      fi
    fi
  done <<< "$filtered_repos"
  
  generate_alfred_footer
}

# Main function that orchestrates the workflow
main() {
  local query="$1"
  
  # Setup configuration and environment
  setup_config "$query"
  
  # Gather repositories from all sources
  local all_repos_raw=$(gather_all_repos)
  
  # Process repositories (deduplicate and sort)
  local all_repos=$(process_repositories "$all_repos_raw")
  
  # Filter repositories based on query
  local filtered_repos=$(filter_repositories "$all_repos" "$QUERY")
  
  # Generate and output Alfred JSON
  generate_alfred_output "$filtered_repos" "$CACHE_DURATION"
}

# Execute main function with all arguments
main "$@"