#!/usr/bin/env python3

import process_text as pt


def test_llm_produces_two_words():
    # Stub llm to return multiple words; function should take first two and hyphen-join
    pt._llm = lambda flags, prompt, input_text=None: "Refactor authentication flow"
    out = pt.generate_branch_name_from_clip("Some context doesn't matter for the stubbed llm")
    assert out["alfredworkflow"]["arg"] == "refactor-authentication"


def test_llm_returns_fenced_and_punctuation():
    # LLM returns fenced text with punctuation / underscores; unwrap and sanitize
    pt._llm = lambda flags, prompt, input_text=None: "```fix_bug: handle-exceptions```"
    out = pt.generate_branch_name_from_clip("ignored")
    # sanitize removes punctuation/underscores and keeps first two tokens
    assert out["alfredworkflow"]["arg"] == "fix-bug"


def test_llm_fails_fallback_to_clip():
    # Simulate LLM failing; function should fallback to input content
    pt._llm = lambda flags, prompt, input_text=None: "llm failed"
    out = pt.generate_branch_name_from_clip("Fix bug: can't save file!")
    assert out["alfredworkflow"]["arg"] == "fix-bug"


def test_empty_clipboard_returns_error():
    out = pt.generate_branch_name_from_clip("")
    assert out["alfredworkflow"]["arg"] == ""
    assert "Clipboard is empty" in out["alfredworkflow"]["variables"]["message"]


def test_do_action_clip_to_branch(capsys, monkeypatch):
    """Integration-style test: run do() with action 'clip_to_branch' and capture stdout JSON."""
    import json, sys, os

    # Stub LLM and set environment/argv
    pt._llm = lambda flags, prompt, input_text=None: "Improve save logic"
    monkeypatch.setenv("entry", "ignored")
    monkeypatch.setattr(sys, "argv", ["process_text.py", "clip_to_branch"])

    # Run do() which writes JSON to stdout
    pt.do()

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["alfredworkflow"]["arg"] == "improve-save"
