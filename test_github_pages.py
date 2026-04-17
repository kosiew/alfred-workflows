import json
import sys
from pathlib import Path

import a_github_pages as gp


def test_publish_clipboard_writes_markdown_file(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv('entry', 'Hello GitHub Pages!')
    monkeypatch.setenv('repo_path', str(tmp_path))
    monkeypatch.setenv('github_pages_url', 'https://kosiew.github.io')
    monkeypatch.setenv('page_filename', 'test-page')
    monkeypatch.setattr(sys, 'argv', ['a_github_pages.py', 'publish'])

    gp.do()

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data['alfredworkflow']['arg'] == 'https://kosiew.github.io/__posts/test-page'
    page_file = Path(data['alfredworkflow']['variables']['page_file'])
    assert page_file.parent == tmp_path / '__posts'
    assert page_file.exists()
    assert page_file.read_text(encoding='utf-8') == 'Hello GitHub Pages!'


def test_publish_writes_post_to_posts_with_date_title_filename(tmp_path, capsys, monkeypatch):
    content = '''---
title: "Consistent Hashing vs Rendezvous Hashing"
date: 2026-04-17
tags: [distributed-systems, hashing, load-balancing, system-design]
---

Rust content body here.'''
    monkeypatch.setenv('entry', content)
    monkeypatch.setenv('repo_path', str(tmp_path))
    monkeypatch.setenv('github_pages_url', 'https://kosiew.github.io')
    monkeypatch.setattr(sys, 'argv', ['a_github_pages.py', 'publish'])

    gp.do()

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    page_file = Path(data['alfredworkflow']['variables']['page_file'])

    assert page_file.parent == tmp_path / '__posts'
    assert page_file.name == '2026-04-17-consistent-hashing-vs-rendezvous-hashing.md'
    post_content = page_file.read_text(encoding='utf-8')
    assert post_content.startswith(content)
    assert '<!-- gh-pages-taxonomy-links:start -->' in post_content
    assert 'Tags: [distributed-systems](/tags/distributed-systems/), [hashing](/tags/hashing/), [load-balancing](/tags/load-balancing/), [system-design](/tags/system-design/)' in post_content
    assert data['alfredworkflow']['arg'] == 'https://kosiew.github.io/__posts/2026-04-17-consistent-hashing-vs-rendezvous-hashing'


def test_publish_returns_tag_category_pages_variables(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv('entry', 'Hello GitHub Pages!')
    monkeypatch.setenv('repo_path', str(tmp_path))
    monkeypatch.setenv('github_pages_url', 'https://kosiew.github.io')
    monkeypatch.setenv('page_filename', 'test-page')
    monkeypatch.setenv('category', 'examples')
    monkeypatch.setenv('tag', 'alpha,beta')
    monkeypatch.setattr(sys, 'argv', ['a_github_pages.py', 'publish'])

    gp.do()

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    variables = data['alfredworkflow']['variables']

    assert variables['category'] == 'examples'
    assert variables['tag'] == 'alpha, beta'
    assert variables['pages'] == 'https://kosiew.github.io/__posts/test-page'


def test_publish_generates_tag_category_pages_from_frontmatter(tmp_path, capsys, monkeypatch):
    content = '''---
    title: "Hello"
    date: 2026-04-17
    categories: [examples, docs]
    tags: [alpha, beta]
    ---

    Body content.'''
    monkeypatch.setenv('entry', content)
    monkeypatch.setenv('repo_path', str(tmp_path))
    monkeypatch.setenv('github_pages_url', 'https://kosiew.github.io')
    monkeypatch.setattr(sys, 'argv', ['a_github_pages.py', 'publish'])

    gp.do()

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    variables = data['alfredworkflow']['variables']
    page_file = Path(variables['page_file'])
    post_content = page_file.read_text(encoding='utf-8')
    alpha_tag_page = tmp_path / 'tags' / 'alpha' / 'index.md'
    examples_category_page = tmp_path / 'categories' / 'examples' / 'index.md'

    assert variables['category'] == 'examples'
    assert variables['tag'] == 'alpha, beta'
    assert variables['pages'] == 'https://kosiew.github.io/__posts/2026-04-17-hello'
    assert '<!-- gh-pages-taxonomy-links:start -->' in post_content
    assert 'Categories: [examples](/categories/examples/), [docs](/categories/docs/)' in post_content
    assert 'Tags: [alpha](/tags/alpha/), [beta](/tags/beta/)' in post_content
    assert alpha_tag_page.exists()
    assert examples_category_page.exists()
    assert '# Tags: alpha' in alpha_tag_page.read_text(encoding='utf-8')
    assert '# Categories: examples' in examples_category_page.read_text(encoding='utf-8')


def test_publish_refreshes_taxonomy_page_with_existing_posts(tmp_path, capsys, monkeypatch):
    posts_dir = tmp_path / '__posts'
    posts_dir.mkdir(parents=True)
    existing_post = posts_dir / '2026-01-01-first-post.md'
    existing_post.write_text(
        '---\n'
        'title: "First post"\n'
        'tags: [alpha]\n'
        'categories: [examples]\n'
        '---\n\n'
        'Body.',
        encoding='utf-8',
    )

    content = '''---
title: "Second post"
date: 2026-04-17
tags: [alpha]
categories: [examples]
---

Body.'''
    monkeypatch.setenv('entry', content)
    monkeypatch.setenv('repo_path', str(tmp_path))
    monkeypatch.setenv('github_pages_url', 'https://kosiew.github.io')
    monkeypatch.setattr(sys, 'argv', ['a_github_pages.py', 'publish'])

    gp.do()

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    variables = data['alfredworkflow']['variables']
    assert variables['tag'] == 'alpha'
    assert variables['category'] == 'examples'

    alpha_tag_page = tmp_path / 'tags' / 'alpha' / 'index.md'
    tag_page_content = alpha_tag_page.read_text(encoding='utf-8')

    assert '- [First post](/__posts/2026-01-01-first-post/)' in tag_page_content
    assert '- [Second post](/__posts/2026-04-17-second-post/)' in tag_page_content


def test_get_page_title_extracts_yaml_frontmatter_title():
    content = '''---
title: "Consistent Hashing vs Rendezvous Hashing"
date: 2026-04-17
tags: [distributed-systems, hashing, load-balancing, system-design]
---

Rust content body here.'''
    assert gp.get_page_title(content) == 'Consistent Hashing vs Rendezvous Hashing'
