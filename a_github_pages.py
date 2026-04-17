import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

ALFREDWORKFLOW = 'alfredworkflow'
ARG = 'arg'
VARIABLES = 'variables'
MESSAGE = 'message'
MESSAGE_TITLE = 'message_title'
PAGE_URL = 'page_url'
PAGE_FILE = 'page_file'

GITHUB_PAGES_URL = os.getenv('github_pages_url', '')
REPO_PATH = os.getenv('repo_path', '')
POSTS_PATH = '_posts'

def output_json(a_dict):
    sys.stdout.write(json.dumps(a_dict))


def build_alfred_response(arg: str = '', message: str = '', message_title: str = '', extra_variables: Optional[dict[str, str]] = None) -> dict:
    variables = {MESSAGE: message, MESSAGE_TITLE: message_title}
    if extra_variables:
        variables.update(extra_variables)
    return {
        ALFREDWORKFLOW: {
            ARG: arg,
            VARIABLES: variables,
        }
    }


def _run(cmd: list[str], cwd: Optional[str] = None, **kw) -> subprocess.CompletedProcess:
    kw.setdefault('check', True)
    kw.setdefault('text', True)
    kw.setdefault('capture_output', True)
    if cwd is not None:
        kw.setdefault('cwd', cwd)
    return subprocess.run(cmd, **kw)


def slugify(text: str, fallback: str = 'page') -> str:
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\s-]", '', slug)
    slug = re.sub(r"[\s_]+", '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug or fallback


def get_clipboard_content() -> str:
    return os.getenv('entry', '')


def get_page_title(content: str) -> str:
    lines = content.splitlines()
    index = 0

    while index < len(lines) and not lines[index].strip():
        index += 1

    if index < len(lines) and lines[index].strip() == '---':
        index += 1
        while index < len(lines):
            line = lines[index].strip()
            if line == '---':
                index += 1
                break
            match = re.match(r'^title:\s*(?P<quote>["\']?)(?P<title>.*?)(?P=quote)\s*$', line)
            if match:
                return match.group('title').strip()[:60]
            index += 1

    for line in lines[index:]:
        line = line.strip()
        if line:
            return line[:60]
    return 'page'


def parse_frontmatter_metadata(content: str) -> tuple[Optional[str], Optional[str]]:
    lines = content.splitlines()
    index = 0

    while index < len(lines) and not lines[index].strip():
        index += 1

    if index >= len(lines) or lines[index].strip() != '---':
        return None, None

    index += 1
    title = None
    date_value = None

    while index < len(lines):
        line = lines[index].strip()
        if line == '---':
            break
        if title is None:
            title_match = re.match(r'^title:\s*(?P<quote>["\']?)(?P<title>.*?)(?P=quote)\s*$', line)
            if title_match:
                title = title_match.group('title').strip()[:60]
        if date_value is None:
            date_match = re.match(r'^date:\s*(?P<quote>["\']?)(?P<date>.+?)(?P=quote)\s*$', line)
            if date_match:
                raw_date = date_match.group('date').strip()
                try:
                    date_value = datetime.date.fromisoformat(raw_date[:10]).isoformat()
                except ValueError:
                    pass
        index += 1

    return title, date_value


def normalize_frontmatter_list_value(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if value.startswith('[') and value.endswith(']'):
        value = value[1:-1]
    return [item.strip().strip('"\'"') for item in re.split(r'[\s,]+', value) if item.strip()]


def parse_frontmatter_list_field(content: str, field_name: str) -> list[str]:
    lines = content.splitlines()
    index = 0

    while index < len(lines) and not lines[index].strip():
        index += 1

    if index >= len(lines) or lines[index].strip() != '---':
        return []

    index += 1
    while index < len(lines):
        line = lines[index].strip()
        if line == '---':
            break
        if line.startswith(f'{field_name}:'):
            value = line[len(f'{field_name}:'):].strip()
            return normalize_frontmatter_list_value(value)
        index += 1

    return []


def insert_tags(content: str, tags: list[str]) -> str:
    if not tags:
        return content

    lines = content.splitlines()
    index = 0

    while index < len(lines) and not lines[index].strip():
        index += 1

    if index < len(lines) and lines[index].strip() == '---':
        index += 1
        while index < len(lines):
            line = lines[index].strip()
            if line == '---':
                break
            if line.startswith('tags:'):
                existing_tags = normalize_frontmatter_list_value(line[len('tags:'):].strip())
                combined = []
                for tag in existing_tags + tags:
                    if tag not in combined:
                        combined.append(tag)
                lines[index] = f"tags: [{', '.join(combined)}]"
                return '\n'.join(lines)
            index += 1
        lines.insert(index, f"tags: [{', '.join(tags)}]")
        return '\n'.join(lines)

    frontmatter = f"---\ntags: [{', '.join(tags)}]\n---\n\n"
    return frontmatter + content


def get_post_filename(content: str) -> str:
    title, date_value = parse_frontmatter_metadata(content)
    if not title:
        title = get_page_title(content)
    if not date_value:
        date_value = datetime.date.today().isoformat()
    return f"{date_value}-{slugify(title)}.md"


def normalize_path(path: str) -> str:
    return os.path.normpath(os.path.expanduser(path))


def create_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    index = 1
    while True:
        candidate = parent / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_page_file(content: str, output_path: Path) -> Path:
    ensure_directory(output_path.parent)
    output_path.write_text(content, encoding='utf-8')
    return output_path


def get_page_url(page_path: Path, repo_root: Path, github_pages_url: str) -> str:
    rel_path = page_path.relative_to(repo_root).as_posix()
    if rel_path.endswith('index.md'):
        rel_path = rel_path[: -len('index.md')]
    elif rel_path.endswith('.md'):
        rel_path = rel_path[: -len('.md')]
    return f"{github_pages_url.rstrip('/')}/{rel_path.lstrip('/')}"


def git_commit_and_push(repo_root: Path, commit_message: str, remote: str, branch: str) -> str:
    try:
        status = _run(['git', 'status', '--porcelain'], cwd=str(repo_root)).stdout.strip()
        if not status:
            return 'No changes to commit.'
        _run(['git', 'add', '.'], cwd=str(repo_root))
        _run(['git', 'commit', '-m', commit_message], cwd=str(repo_root))
        _run(['git', 'push', remote, branch], cwd=str(repo_root))
        return f'Pushed to {remote}/{branch}.'
    except subprocess.CalledProcessError as exc:
        return f'Git failed: {exc.stderr.strip() or exc}'


def get_relative_page_url(page_path: Path, repo_root: Path) -> str:
    rel_path = page_path.relative_to(repo_root).as_posix()
    if rel_path.endswith('index.md'):
        rel_path = rel_path[: -len('index.md')]
    elif rel_path.endswith('.md'):
        rel_path = rel_path[: -len('.md')]
    return f"/{rel_path.strip('/')}/"


def is_full_datetime_with_tz(value: str) -> bool:
    try:
        datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S %z')
        return True
    except ValueError:
        return False


def current_utc_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S %z')


def normalize_frontmatter(content: str) -> str:
    lines = content.splitlines()
    index = 0

    while index < len(lines) and not lines[index].strip():
        index += 1

    if index >= len(lines) or lines[index].strip() != '---':
        return content

    closing = index + 1
    malformed = False
    while closing < len(lines):
        line = lines[closing].strip()
        if re.fullmatch(r'-{3,}', line):
            if line != '---':
                lines[closing] = '---'
                malformed = True
            break
        closing += 1

    if closing >= len(lines):
        lines.insert(closing, '---')
        malformed = True

    if malformed:
        date_line = None
        for inner in range(index + 1, closing):
            match = re.match(r'^date:\s*(?P<quote>["\']?)(?P<date>.*?)(?P=quote)\s*$', lines[inner])
            if match:
                raw_date = match.group('date').strip()
                if not is_full_datetime_with_tz(raw_date):
                    lines[inner] = f"date: {current_utc_timestamp()}"
                date_line = inner
                break

        if date_line is None:
            lines.insert(index + 1, f"date: {current_utc_timestamp()}")

    normalized = '\n'.join(lines)
    if content.endswith('\n'):
        normalized += '\n'
    return normalized


def build_taxonomy_link_line(label: str, values: list[str], base_path: str) -> str:
    if not values:
        return ''
    links = [f"[{value}]({base_path}/{slugify(value)}/)" for value in values]
    return f"{label}: {', '.join(links)}"


def upsert_taxonomy_links(content: str, tags: list[str], categories: list[str]) -> str:
    marker_start = '<!-- gh-pages-taxonomy-links:start -->'
    marker_end = '<!-- gh-pages-taxonomy-links:end -->'

    category_line = build_taxonomy_link_line('Categories', categories, '/categories')
    tag_line = build_taxonomy_link_line('Tags', tags, '/tags')

    body_lines = [line for line in [category_line, tag_line] if line]
    if not body_lines:
        return content

    block_lines = [
        marker_start,
        *body_lines,
        marker_end,
    ]
    block = '\n'.join(block_lines)
    pattern = re.compile(rf"{re.escape(marker_start)}.*?{re.escape(marker_end)}", re.DOTALL)

    if pattern.search(content):
        return pattern.sub(block, content)

    if content.endswith('\n'):
        return f"{content}\n{block}\n"
    return f"{content}\n\n{block}\n"


def resolve_category_value(category: str, frontmatter_categories: list[str], frontmatter_tags: list[str]) -> str:
    if category:
        return category
    if frontmatter_categories:
        return frontmatter_categories[0]
    if frontmatter_tags:
        return frontmatter_tags[0]
    return ''


def resolve_category_list(frontmatter_categories: list[str], resolved_category: str) -> list[str]:
    categories: list[str] = []
    for candidate in frontmatter_categories + ([resolved_category] if resolved_category else []):
        if candidate and candidate not in categories:
            categories.append(candidate)
    return categories


def resolve_tags_list(tag_value: str, frontmatter_tags: list[str], category: str, first_frontmatter_tag: str) -> list[str]:
    tags = normalize_frontmatter_list_value(tag_value) if tag_value else frontmatter_tags
    if not tags and category and category != first_frontmatter_tag:
        tags = [category]
    return tags


def update_post_content(content: str, category: str, tags: list[str], tag_value: str, categories: list[str]) -> tuple[str, list[str], list[str]]:
    if os.getenv('category', '').strip():
        content = insert_category(content, category)
    if tag_value:
        content = insert_tags(content, tags)

    parsed_categories = parse_frontmatter_list_field(content, 'categories')
    parsed_tags = parse_frontmatter_list_field(content, 'tags')
    categories = parsed_categories or categories
    tags = parsed_tags or tags
    content = upsert_taxonomy_links(content, tags, categories)
    return content, categories, tags


def insert_category(content: str, category: str) -> str:
    if not category:
        return content

    lines = content.splitlines()
    index = 0

    while index < len(lines) and not lines[index].strip():
        index += 1

    if index < len(lines) and lines[index].strip() == '---':
        closing = index + 1
        while closing < len(lines) and lines[closing].strip() != '---':
            closing += 1

        if closing >= len(lines):
            frontmatter = f"---\ncategories: {category}\n---\n\n"
            return frontmatter + content

        for inner in range(index + 1, closing):
            line = lines[inner].strip()
            if line.startswith('categories:'):
                existing_categories = line[len('categories:'):].strip()
                if existing_categories:
                    categories_list = [c.strip() for c in existing_categories.split(',') if c.strip()]
                    if category not in categories_list:
                        categories_list.append(category)
                        lines[inner] = f"categories: {', '.join(categories_list)}"
                else:
                    lines[inner] = f"categories: {category}"
                return '\n'.join(lines)

        lines.insert(closing, f"categories: {category}")
        return '\n'.join(lines)

    frontmatter = f"---\ncategories: {category}\n---\n\n"
    return frontmatter + content

def publish(content: Optional[str] = None) -> dict:
    if not content:
        return build_alfred_response('', 'Clipboard is empty', 'Error')


    repo_root = Path(normalize_path(os.getenv('repo_path', '')))
    if not repo_root.exists():
        return build_alfred_response('', f'Repo path does not exist: {repo_root}', 'Invalid repo path')

    github_pages_url = os.getenv('github_pages_url', '')
    filename = os.getenv('page_filename', '').strip()
    category = os.getenv('category', '').strip()
    tag_value = os.getenv('tag', '').strip()

    content = normalize_frontmatter(content)
    frontmatter_categories = parse_frontmatter_list_field(content, 'categories')
    frontmatter_tags = parse_frontmatter_list_field(content, 'tags')

    category = resolve_category_value(category, frontmatter_categories, frontmatter_tags)
    categories = resolve_category_list(frontmatter_categories, category)
    tags = resolve_tags_list(tag_value, frontmatter_tags, category, frontmatter_tags[0] if frontmatter_tags else '')

    if not filename:
        filename = get_post_filename(content)
    if not Path(filename).suffix:
        filename = f"{filename}.md"

    output_dir = repo_root / POSTS_PATH
    file_path = output_dir / filename
    file_path = create_unique_path(file_path)

    content, categories, tags = update_post_content(content, category, tags, tag_value, categories)
    write_page_file(content, file_path)

    page_url = get_page_url(file_path, repo_root, github_pages_url)
    message_title = 'Saved GitHub Pages content'
    message = str(file_path)

    if os.getenv('commit_and_push', 'N').upper() == 'Y':
        commit_message = os.getenv('commit_message', f'Publish {file_path.name}')
        remote = os.getenv('git_remote', 'origin')
        branch = os.getenv('git_branch', 'main')
        git_result = git_commit_and_push(repo_root, commit_message, remote, branch)
        message_title = 'Published to GitHub Pages'
        message = f'{file_path} — {git_result}'

    return build_alfred_response(
        page_url,
        message,
        message_title,
        {
            PAGE_URL: page_url,
            PAGE_FILE: str(file_path),
            'tag': ', '.join(tags) if tags else '',
            'category': category,
            'pages': page_url,
        },
    )


def do() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else ''
    
    entry = os.getenv('entry')
    if action == 'publish':
        output_json(publish(entry))
    else:
        output_json(build_alfred_response('', f'Unknown action: {action}', 'Invalid action'))
