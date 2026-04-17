import json
import sys
from pathlib import Path

import a_github_pages as gp


def test_publish_clipboard_writes_markdown_file(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv('entry', 'Hello GitHub Pages!')
    monkeypatch.setenv('github_pages_repo', str(tmp_path))
    monkeypatch.setenv('github_pages_url', 'https://kosiew.github.io')
    monkeypatch.setenv('page_filename', 'test-page')
    monkeypatch.setattr(sys, 'argv', ['a_github_pages.py', 'publish_clipboard'])

    gp.do()

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data['alfredworkflow']['arg'] == 'https://kosiew.github.io/test-page'
    page_file = Path(data['alfredworkflow']['variables']['page_file'])
    assert page_file.exists()
    assert page_file.read_text(encoding='utf-8') == 'Hello GitHub Pages!'


def test_get_page_title_extracts_yaml_frontmatter_title():
    content = '''---
title: "Consistent Hashing vs Rendezvous Hashing"
date: 2026-04-17
tags: [distributed-systems, hashing, load-balancing, system-design]
---

Rust content body here.'''
    assert gp.get_page_title(content) == 'Consistent Hashing vs Rendezvous Hashing'
