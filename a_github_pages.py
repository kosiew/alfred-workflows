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

GITHUB_PAGES_URL = os.getenv('github_pages_url', 'https://kosiew.github.io')

REPO_PATH = Path("~/GitHub/kosiew.github.io")  
POSTS_DIR = REPO_PATH / "_posts"



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
    for line in content.splitlines():
        line = line.strip()
        if line:
            return line[:60].strip()
    return 'page'


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


def get_page_url(page_path: Path, repo_root: Path) -> str:
    rel_path = page_path.relative_to(repo_root).as_posix()
    if rel_path.endswith('index.md'):
        rel_path = rel_path[: -len('index.md')]
    elif rel_path.endswith('.md'):
        rel_path = rel_path[: -len('.md')]
    return f"{GITHUB_PAGES_URL.rstrip('/')}/{rel_path.lstrip('/')}"


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


def publish_clipboard(content: Optional[str] = None) -> dict:
    if not content:
        return build_alfred_response('', 'Clipboard is empty', 'Error')


    repo_root = Path(normalize_path(REPO_PATH))
    if not repo_root.exists():
        return build_alfred_response('', f'Repo path does not exist: {repo_root}', 'Invalid repo path')

    filename = os.getenv('page_filename', '').strip()
    subdir = os.getenv('page_subdir', '').strip()
    if not filename:
        filename = f"{slugify(get_page_title(content))}.md"
    if not Path(filename).suffix:
        filename = f"{filename}.md"

    output_dir = repo_root / subdir if subdir else repo_root
    file_path = output_dir / filename
    file_path = create_unique_path(file_path)
    write_page_file(content, file_path)

    page_url = get_page_url(file_path, repo_root)
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
        {PAGE_URL: page_url, PAGE_FILE: str(file_path)},
    )


def do() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else ''
    
    entry = os.getenv('entry')
    if action == 'publish_clipboard' or action == 'save_clipboard':
        output_json(publish_clipboard(entry))
    else:
        output_json(build_alfred_response('', f'Unknown action: {action}', 'Invalid action'))
