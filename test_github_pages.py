import json
import re
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

    assert data['alfredworkflow']['arg'] == 'https://kosiew.github.io/_posts/test-page'
    page_file = Path(data['alfredworkflow']['variables']['page_file'])
    assert page_file.parent == tmp_path / '_posts'
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

    assert page_file.parent == tmp_path / '_posts'
    assert page_file.name == '2026-04-17-consistent-hashing-vs-rendezvous-hashing.md'
    post_content = page_file.read_text(encoding='utf-8')
    assert post_content.startswith(content)
    assert data['alfredworkflow']['arg'] == 'https://kosiew.github.io/_posts/2026-04-17-consistent-hashing-vs-rendezvous-hashing'


def test_publish_rectifies_malformed_frontmatter(tmp_path, capsys, monkeypatch):
    content = '''---
layout: post
title: "Rust patterns"
date: 2026-04-17
tags: [rust, systems-programming, design-patterns, ownership, safety]
----------------

Body content.'''
    monkeypatch.setenv('entry', content)
    monkeypatch.setenv('repo_path', str(tmp_path))
    monkeypatch.setenv('github_pages_url', 'https://kosiew.github.io')
    monkeypatch.setattr(sys, 'argv', ['a_github_pages.py', 'publish'])

    gp.do()

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    page_file = Path(data['alfredworkflow']['variables']['page_file'])
    post_content = page_file.read_text(encoding='utf-8')

    assert '---\nlayout: post\ntitle: "Rust patterns"\n' in post_content
    assert re.search(r'^date: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}$', post_content, re.MULTILINE)
    assert '\n---\n\nBody content.' in post_content


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
    assert variables['pages'] == 'https://kosiew.github.io/_posts/test-page'


def test_publish_parses_frontmatter_category_tag_variables(tmp_path, capsys, monkeypatch):
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

    assert variables['category'] == 'examples'
    assert variables['tag'] == 'alpha, beta'
    assert variables['pages'] == 'https://kosiew.github.io/_posts/2026-04-17-hello'
    assert post_content.startswith(content)


def test_get_page_title_extracts_yaml_frontmatter_title():
    content = '''---
title: "Consistent Hashing vs Rendezvous Hashing"
date: 2026-04-17
tags: [distributed-systems, hashing, load-balancing, system-design]
---

Rust content body here.'''
    assert gp.get_page_title(content) == 'Consistent Hashing vs Rendezvous Hashing'
