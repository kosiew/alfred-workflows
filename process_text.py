import sys
import re
import json
import os
import subprocess  # newly added
from pathlib import Path  # newly added
import time  # newly added
import html2text  # for HTML to markdown conversion
from python_import_helpers import parse_python_import_statements, generate_python_import_statements
from typing import Optional

# Full path to llm executable (aliases won't be available inside subprocess)
LLM_PATH = "/Users/kosiew/GitHub/llm/.venv/bin/llm"

# Constants for Alfred workflow
ITEMS = "items"
TITLE = "title"
SUBTITLE = "subtitle"
ARG = "arg"
VARIABLES = "variables"
MESSAGE = "message"
MESSAGE_TITLE = "message_title"
ALFREDWORKFLOW = "alfredworkflow"
ENTRY = "entry"
MEANING = "meaning"
WORD = "word"
WHATSAPP_NUMBER = "whatsapp_number"


def output_json(a_dict):
    """Outputs a dictionary as JSON to stdout."""
    sys.stdout.write(json.dumps(a_dict))


def make_alfred_output(arg_value, variables: dict | None = None):
    """Create a standard Alfred workflow output dict.

    Args:
        arg_value: The value to place in the top-level "arg" field.
        variables: Optional dictionary of variables to place under "variables".

    Returns:
        A dict shaped as {ALFREDWORKFLOW: {ARG: arg_value, VARIABLES: {...}}}
    """
    if variables is None:
        variables = {}
    return {
        ALFREDWORKFLOW: {
            ARG: arg_value,
            VARIABLES: variables,
        }
    }

def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    kw.setdefault("check", True)
    kw.setdefault("text", True)
    kw.setdefault("capture_output", True)
    return subprocess.run(cmd, **kw)

def _llm(flags: list[str], prompt: str, input_text: Optional[str] = None) -> str:
    """Call llm CLI tool with the given flags and prompt.
    
    Returns the stdout output, or raises an exception if the command fails.
    Note: Uses full path to llm since subprocess doesn't expand shell aliases.
    """
    try:
        # Use the module-level LLM_PATH constant
        proc = _run([LLM_PATH, *flags, prompt], input=input_text)
        return proc.stdout or ""
    except Exception:
        return "llm failed"

def _unwrap_fenced(text: str) -> str:
    """Remove markdown code fences from text if present."""
    lines = text.strip().split("\n")
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1])
    return text

def process_text(text):
    """Formats text by censoring the first word and replacing later occurrences with '~'."""
    # Extract the first two lines
    lines = text.split("\n", 2)
    first_2_lines = "\n".join(lines[:2]) if len(lines) >= 2 else text

    # Extract words from the text
    words = text.split()
    if not words:
        return first_2_lines, text  # If empty input, return unchanged

    first_word = words[0]  # Get first word as the target
    first_word_pattern = re.escape(first_word)  # Escape special characters if any

    # Censor first word (e.g., "languid" → "l....d")
    if len(first_word) > 2:
        censored_word = first_word[0] + "...." + first_word[-1]
    else:
        censored_word = first_word  # Short words remain unchanged

    count = 0  # Track occurrences

    def replacer(match):
        """Replace occurrences after the first"""
        nonlocal count
        count += 1
        return censored_word if count == 1 else "~"

    # Replace only full-word occurrences
    transformed_text = re.sub(rf"{re.escape(first_word_pattern)}", replacer, text)

    return first_2_lines, transformed_text

def check_diff_version(input_text):
    """
    Returns 1 if any line starts with '+' or '-', else returns 2.
    """
    for line in input_text.split("\n"):
        if line.startswith("+") or line.startswith("-"):
            return 1
    return 2


def show_diffed_result(input_text):
    """
    Processes the input text to show a diffed result.
    - For snapshot diff lines (those containing '│' or '|'), drop everything before and including that symbol.
    - Then:
      * Drop lines starting with '-'
      * Replace a leading '+' with a single space (preserving indentation)
      * Keep all other lines exactly as is
    """
    return _show_diffed_result(input_text, reverse=False)

def show_reverse_diffed_result(input_text):
    """
    Processes the input text to show a reverse diffed result.
    - For snapshot diff lines (those containing '│' or '|'), drop everything before and including that symbol.
    - Then:
      * Drop lines starting with '+'
      * Replace a leading '-' with a single space (preserving indentation)
      * Keep all other lines exactly as is
    """
    return _show_diffed_result(input_text, reverse=True)

def _show_diffed_result(input_text, reverse=False):
    """
    - For snapshot diff (version 2) lines (those containing '│' or '|'), drop everything before and including that symbol.
    - Then:
      * Drop lines starting with '-'
      * Replace a leading '+' with a single space (preserving indentation)
      * Keep all other lines exactly as is
    """
    version = check_diff_version(input_text)
    output = []
    for line in input_text.split("\n"):
        # Only for version 2, remove the prefix up to the first '│' or '|'
        if version == 2 and ('│' in line or '|' in line):
            # split on either box-drawing or ascii pipe, max once
            parts = re.split(r"[│|]", line, maxsplit=1)
            if len(parts) >= 2:
                line = parts[1]

        # Now treat it like version 1
        if reverse:
            if line.startswith("+"):
                continue
            if line.startswith("-"):
                line = " " + line[1:]
        else:
            if line.startswith("-"):
                continue
            if line.startswith("+"):
                line = " " + line[1:]

        output.append(line)

    return "\n".join(output)

def rename_dalle_files():
    try:
        downloads_dir = Path.home() / "Downloads"

        few_min_ago = time.time() - 60 * 5

        all_recent = [
            f for f in downloads_dir.iterdir() if f.stat().st_mtime > few_min_ago
        ]

        recent_files = [
            f for f in downloads_dir.glob("DALL*") if f.stat().st_mtime > few_min_ago
        ]

        if not recent_files:
            raise Exception("No recent DALL-E files found.")

        recent_file = max(recent_files, key=lambda f: f.stat().st_mtime)

        strip_metadata(recent_file)

        # Run llm to get a short name
        result = shorten(recent_file, 2)
        short_name_base = result

        if not short_name_base:
            raise Exception("llm returned an empty name.")

        # Retain the file extension
        file_extension = recent_file.suffix
        short_name = f"{short_name_base}{file_extension}"

        new_path = recent_file.parent / short_name
        recent_file.rename(new_path)

        output = make_alfred_output(short_name, {MESSAGE: f"Renamed → {short_name}", MESSAGE_TITLE: "Rename Success"})
    except Exception as e:
        output = make_alfred_output(str(e), {MESSAGE: f"Error: {e}", MESSAGE_TITLE: "Rename Failed"})

    return output


def shorten(phrase, number_of_words=2):
    result = subprocess.run(
        [LLM_PATH, "-m", "l32", f"shorten to {number_of_words} meaningful unique word"],
        input=phrase.name,
        text=True,
        capture_output=True,
        check=True,
    )

    # Extract only the actual words, removing any introduction text and quotes
    output = result.stdout.strip()

    # Find the last N words, stripping quotes
    words = output.split()
    clean_output = " ".join(words[-number_of_words:]).replace('"', "").replace("'", "")

    return clean_output


from rust_import_helpers import (
    parse_import_statements, 
    group_imports_by_base_path,
    generate_import_statements
)
from rust_import_helpers import (
    process_import_with_braces,
    collect_root_groups,
    highest_common_subpath,
    format_high_group,
    collect_low_groups,
)

def streamline_rust_imports(text):
    return streamline_rust_imports_unique(text)

# deprecated this
# it is neither ..low or ..high
def _streamline_rust_imports(text):
    """Streamlines Rust import statements by consolidating imports with the same base path."""
    if not text or text.isspace():
        return text

    # Split the text into lines
    lines = text.strip().split("\n")
    
    # Parse the import statements
    use_statements, other_lines = parse_import_statements(lines)
    
    # Group imports by base path
    grouped_by_base, special_imports = group_imports_by_base_path(use_statements)
    
    # Generate the consolidated import statements
    result = generate_import_statements(grouped_by_base, special_imports)
    
    # Combine with other non-import lines
    if other_lines and result:
        return "\n".join(other_lines + [""] + result)
    return "\n".join(other_lines + result)


    



def streamline_rust_imports_high(text):
    """Streamline Rust imports grouping at the highest (root) module level.

    This follows the behavior described for the older commit that groups
    imports by the top-level/root module (e.g. `arrow::{...}` instead of
    `arrow::array::{...}`).
    """
    if not text or text.isspace():
        return text

    lines = text.strip().split("\n")
    use_statements, other_lines = parse_import_statements(lines)

    root_groups, special_imports = collect_root_groups(use_statements)

    result = []
    for cfg_attr, stmt, _ in special_imports:
        if cfg_attr:
            result.append(cfg_attr)
        result.append(stmt)

    for (root, is_pub) in sorted(root_groups.keys()):
        group = root_groups[(root, is_pub)]
        common_sub = highest_common_subpath(group)
        result.extend(format_high_group(root, is_pub, group, common_sub))

    if other_lines and result:
        return "\n".join(other_lines + [""] + result)
    return "\n".join(other_lines + result)


def streamline_rust_imports_low(text):
    """Streamline Rust imports grouping at the lowest (most-specific) module level.

    This groups imports by the most specific module path (everything except the
    final item). Example: `arrow::array::ArrayRef` -> base `arrow::array` with
    item `ArrayRef`. Multi-item/braced imports are expanded via
    `process_import_with_braces`.
    """
    if not text or text.isspace():
        return text

    lines = text.strip().split("\n")
    use_statements, other_lines = parse_import_statements(lines)

    grouped_by_base, special_imports = collect_low_groups(use_statements)
    result = generate_import_statements(grouped_by_base, special_imports)

    if other_lines and result:
        return "\n".join(other_lines + [""] + result)
    return "\n".join(other_lines + result)


def _is_covered_by(prev_key, new_key):
    prev_cfg, prev_pub, prev_paths = prev_key
    new_cfg, new_pub, new_paths = new_key
    if prev_cfg != new_cfg or prev_pub != new_pub:
        return False

    for new_item in new_paths:
        covered = False
        for prev_item in prev_paths:
            if prev_item == new_item:
                covered = True
                break
            if prev_item.endswith("::*"):
                prefix = prev_item[:-3]
                if new_item == prefix or new_item.startswith(prefix + "::"):
                    covered = True
                    break
        if not covered:
            return False
    return True

def _canonicalize_import(cfg_attr: str | None, stmt_str: str):
    """Return a canonical key representing the import's semantics.

    cfg_attr: the cfg attribute string (or None)
    stmt_str: the stripped import string like 'use foo::bar::{A, B}' or 'use foo::X'

    The key is a tuple: (cfg_norm, is_pub, frozenset(full_paths)) where
    full_paths are fully-qualified import paths like 'foo::bar::A', or
    a special wildcard marker 'foo::*' for glob imports.
    """
    # Normalize cfg attribute by removing interior whitespace so
    # variants like '#[cfg(feature = "x")]' and '#[cfg( feature="x" )]'
    # are treated as equivalent when deduplicating.
    cfg_norm = re.sub(r"\s+", "", (cfg_attr or "")).strip()

    is_pub = stmt_str.startswith("pub use ")
    prefix_len = 8 if is_pub else 4
    import_path = stmt_str[prefix_len:-1].strip()  # drop trailing ';'

    # Wildcard imports remain distinct
    if import_path.endswith("::*"):
        return (cfg_norm, is_pub, (import_path,))

    full_paths = set()

    # Braced imports
    if "{" in import_path:
        mapping = process_import_with_braces(import_path)
        for base_path, items in mapping.items():
            for item in items:
                if item == 'self':
                    full_paths.add(base_path)
                else:
                    full_paths.add(f"{base_path}::{item}")
    else:
        # Simple import: full path is the join of parts
        parts = [p for p in import_path.split("::") if p]
        if parts:
            full_paths.add("::".join(parts))

    return (cfg_norm, is_pub, tuple(sorted(full_paths)))


def _collect_import_block(lines: list[str], start_idx: int):
    """Collects an import statement block starting at start_idx.

    Returns a tuple: (stmt_lines, end_idx, compact_stmt_str)
    - stmt_lines: list of original lines belonging to the import (preserves original formatting)
    - end_idx: index of the last line of the import block
    - compact_stmt_str: a compact single-line representation suitable for canonicalization

    The function handles single-line imports (ending with ';') and
    multi-line braced imports which end with a line that endswith '};'.
    """
    if start_idx >= len(lines):
        return [], start_idx, ""

    first = lines[start_idx]
    first_stripped = first.strip()

    # Single-line import
    if first_stripped.endswith(";"):
        return [first], start_idx, first_stripped

    # Multi-line braced import
    stmt_lines = [first]
    j = start_idx + 1
    while j < len(lines) and not lines[j].strip().endswith("};"):
        stmt_lines.append(lines[j])
        j += 1
    if j < len(lines):
        stmt_lines.append(lines[j])

    compact = " ".join([ln.strip() for ln in stmt_lines])
    return stmt_lines, j, compact

def streamline_rust_imports_unique(text):
    """Ensure there are no duplicate Rust imports in `text`.

    This function parses the existing `use`/`pub use` statements, groups
    them by base path (deduplicating items using sets) and then
    regenerates consolidated import statements. The result will contain
    no duplicate imports while preserving cfg attributes and other non-
    import lines.
    """
    if not text or text.isspace():
        return text

    # We only want to remove duplicate imports. To be helpful we will
    # canonicalize import statements so that semantically equivalent
    # but textually-different imports (spacing, braced vs simple forms,
    # nested braces) are treated as duplicates, while preserving the
    # original formatting and ordering of the first occurrence.


    # We'll scan the original lines and skip imports we've already seen
    lines = text.split("\n")
    out_lines = []
    # Keep a list of seen canonical entries: (cfg_norm, is_pub, set(full_paths))
    seen_entries: list[tuple[str, bool, set]] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Handle cfg-attribute followed by an import
        if stripped.startswith("#[cfg") and i + 1 < len(lines):
            next_line = lines[i + 1]
            next_stripped = next_line.strip()
            if next_stripped.startswith("pub use ") or next_stripped.startswith("use "):
                # collect the import block (single-line or multi-line) after the cfg
                stmt_lines, j, full_stmt = _collect_import_block(lines, i + 1)

                key = _canonicalize_import(stripped, full_stmt)

                if not any(_is_covered_by(prev, key) for prev in seen_entries):
                    seen_entries.append((key[0], key[1], set(key[2])))
                    out_lines.append(line)  # cfg line
                    out_lines.extend(stmt_lines)

                # Advance i past the cfg + import block
                i = j + 1
                continue

        # Handle plain use / pub use statements
        if stripped.startswith("pub use ") or stripped.startswith("use "):
            # collect the import block (single-line or multi-line)
            stmt_lines, j, stmt_text = _collect_import_block(lines, i)
            key = _canonicalize_import(None, stmt_text)

            if not any(_is_covered_by(prev, key) for prev in seen_entries):
                seen_entries.append((key[0], key[1], set(key[2])))
                out_lines.extend(stmt_lines)

            i = j + 1
            continue

        # Non-import line: preserve
        out_lines.append(line)
        i += 1

    return "\n".join(out_lines)

def remove_rust_printlns(text):
    """Removes println!("==> ...") statements from Rust code, including multi-line ones."""
    if not text or text.isspace():
        return text

    # Split into lines and add a line index
    lines = text.strip().split("\n")
    filtered_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this line starts a debug println
        if "println!" in line and (
            "==> " in line
            or (
                line.strip().endswith("println!(")
                and i + 1 < len(lines)
                and "==> " in lines[i + 1]
            )
        ):
            # Found a debug println, now find where it ends
            j = i

            # Continue until we find the closing pattern ");", accounting for possible strings containing ");"
            while ");" not in lines[j]:
                j += 1
                if j >= len(lines):
                    break  # Malformed code - reached end without closing

            # Skip all lines that were part of this println
            i = j + 1
            continue
        else:
            # Keep this line
            filtered_lines.append(line)
            i += 1

    return "\n".join(filtered_lines)


def remove_python_prints(text):
    """Removes print("==> ...") or print('==> ...') statements from Python code, including multi-line ones."""
    if not text or text.isspace():
        return text

    lines = text.strip().split("\n")
    filtered_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this line starts a debug print statement (with single or double quotes)
        if "print(" in line and (
            '"==> ' in line
            or "'==> " in line
            or (
                line.strip().endswith("print(")
                and i + 1 < len(lines)
                and ('"==> ' in lines[i + 1] or "'==> " in lines[i + 1])
            )
        ):
            # Found a debug print, now find where it ends
            j = i

            # Continue until we find the closing parenthesis
            while ")" not in lines[j]:
                j += 1
                if j >= len(lines):
                    break  # Malformed code - reached end without closing

            # Skip all lines that were part of this print
            i = j + 1
            continue
        else:
            # Keep this line
            filtered_lines.append(line)
            i += 1

    return "\n".join(filtered_lines)


def strip_metadata(image_path):
    """
    Strips all metadata, including C2PA, from the given image file using exiftool.
    """
    if not os.path.exists(image_path):
        return False, f"File not found: {image_path}"

    try:
        # Remove metadata and overwrite the original image
        subprocess.run(
            ["exiftool", "-all=", "-overwrite_original", image_path], check=True
        )
        return True, f"Metadata stripped from {image_path}"
    except subprocess.CalledProcessError as e:
        return False, f"Error while stripping metadata: {e}"
    except FileNotFoundError:
        return (
            False,
            "Error: exiftool not installed. Install with 'brew install exiftool'",
        )


def split_text_at_string(input_text, search_string):
    """
    Split input text around a search string.
    
    Args:
        input_text: The text to split
        search_string: The string to split at
    
    Returns:
        tuple: (pre, post)
            - pre: Text before the search string (or entire input if not found)
            - post: Text after the search string (or empty string if not found)
    """
    if search_string in input_text:
        pre, post = input_text.split(search_string, 1)
    else:
        pre = input_text
        post = ""
    
    return pre, post


def check_string_match(input_text, search_string):
    """
    Check if search string exists in input text.
    
    Args:
        input_text: The text to search in
        search_string: The string to search for
    
    Returns:
        str: "Y" if search string is found, "N" if not found
    """
    return "Y" if search_string in input_text else "N"


def streamline_python_imports(text):
    """Streamlines Python import statements by consolidating imports from the same module."""
    if not text or text.isspace():
        return text

    # Split the text into lines
    lines = text.strip().split("\n")
    
    # Parse the import statements
    simple_imports, from_imports = parse_python_import_statements(lines)
    
    # Generate the consolidated import statements
    result = generate_python_import_statements(simple_imports, from_imports)
    
    return "\n".join(result)


def remove_plus_prefix(text):
    """Removes '+' and '-' prefix from lines in the input text."""
    if not text or text.isspace():
        return text

    lines = text.strip().split("\n")
    filtered_lines = []

    for line in lines:
        if line.startswith("+") or line.startswith("-"):
            # Remove the '+' or '-' and any immediately following whitespace
            cleaned_line = line[1:].lstrip()
            filtered_lines.append(cleaned_line)
        else:
            filtered_lines.append(line)

    return "\n".join(filtered_lines)


def remove_spaces(text):
    """Removes all spaces from the input text."""
    if not text:
        return text
    
    return text.replace(" ", "")


def html_to_markdown(html_content):
    """Converts HTML content to markdown format."""
    try:
        # Create html2text instance
        h = html2text.HTML2Text()
        
        # Configure options for better conversion
        h.ignore_links = False  # Keep links
        h.ignore_images = False  # Keep images
        h.ignore_emphasis = False  # Keep bold/italic
        h.body_width = 0  # Don't wrap lines
        h.unicode_snob = True  # Use unicode characters
        h.escape_snob = True  # Escape special characters
        
        # Convert HTML to markdown
        markdown_content = h.handle(html_content)
        
        # Clean up extra newlines
        markdown_content = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown_content)
        
        return markdown_content.strip()
    except Exception as e:
        # Fallback: basic HTML tag removal if html2text fails
        # Remove common HTML tags
        text = re.sub(r'<br\s*/?>', '\n', html_content)
        text = re.sub(r'<p[^>]*>', '\n', text)
        text = re.sub(r'</p>', '\n', text)
        text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text)
        text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text)
        text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text)
        text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text)
        text = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', text)
        text = re.sub(r'<[^>]+>', '', text)  # Remove remaining tags
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Clean up newlines
        return text.strip()


def generate_commit_message_from_clip(clip_content: str):
    """Generate a git commit message from clipboard content using the LLM and
    return the Alfred JSON output dictionary.

    This mirrors the previous inline implementation in the `clip_to_commit`
    branch: it validates input, calls the LLM with a full prompt, unwraps
    fenced output, and returns the appropriate Alfred-formatted dict.
    """
    if not clip_content:
        return make_alfred_output("", {MESSAGE: "Clipboard is empty", MESSAGE_TITLE: "Error"})

    # Build the full prompt similar to the previous inline code
    full_prompt = (
        f"Generate a git commit message for the following changes. "
        f"Use imperative mood, max 50 chars for subject, blank line, "
        f"then a short body wrapped at ~72 chars. Do not include code fences.\n\n"
    )

    try:
        llm_output = _llm([], full_prompt, input_text=f"Changes:\n{clip_content}")

        if not llm_output or llm_output == "llm failed":
            llm_output = ""

        commit_msg = _unwrap_fenced(llm_output).strip()

        if not commit_msg:
            return make_alfred_output("", {MESSAGE: "LLM returned empty commit message", MESSAGE_TITLE: "Error"})

        return make_alfred_output(commit_msg, {MESSAGE: "Commit message generated!", MESSAGE_TITLE: "Success"})
    except Exception as e:
        return make_alfred_output("", {MESSAGE: f"LLM generation failed: {str(e)}", MESSAGE_TITLE: "Error"})


def generate_commit_range_from_clip(clip_content: str):
    """Parse a git log-like clipboard content and return Alfred VARIABLES
    containing 'start' (oldest commit in list) and 'end' (newest commit in list).

    The input is expected to contain commit lines that start with a SHA (7+ hex
    chars). We will collect all SHAs in the text in appearance order and then
    set 'end' to the first SHA found (newest) and 'start' to the last SHA found
    (oldest).
    """
    if not clip_content:
        return make_alfred_output("", {MESSAGE: "Clipboard is empty", MESSAGE_TITLE: "Error"})

    # Regex to find commit SHAs (7 to 40 hex chars) at the start of a line or after a pipe/symbol
    sha_regex = re.compile(r"\b([0-9a-f]{7,40})\b", re.IGNORECASE)

    shas = sha_regex.findall(clip_content)

    # Deduplicate while preserving order
    seen = set()
    ordered_shas = []
    for s in shas:
        if s not in seen:
            seen.add(s)
            ordered_shas.append(s)

    if not ordered_shas:
        return make_alfred_output("", {MESSAGE: "No commit SHAs found in clipboard", MESSAGE_TITLE: "Error"})

    # Newest is first appearance, oldest is last
    end_sha = ordered_shas[0]
    start_sha = ordered_shas[-1]

    return make_alfred_output(f"{start_sha}..{end_sha}", {MESSAGE: "Commit range prepared", MESSAGE_TITLE: "Success", "start": start_sha, "end": end_sha})


def generate_branch_name_from_clip(clip_content: str):
    """Generate a 1-2 word hyphen-joined summary suitable for a git branch name
    from clipboard content. This mirrors the commit-message generator but
    returns a short, sanitized string that contains only lowercase letters,
    numbers and hyphens (max two words).
    """
    if not clip_content:
        return make_alfred_output("", {MESSAGE: "Clipboard is empty", MESSAGE_TITLE: "Error"})

    # Ask the LLM for a very short 1-2 word summary suitable as a branch name
    prompt = (
        "Generate a 1-2 word short summary suitable for a git branch name from the "
        "following content. Return only the words, lower-case, no surrounding text, "
        "no code fences. Prefer concise nouns or verb-noun pairs."
    )

    try:
        llm_output = _llm([], prompt, input_text=f"Content:\n{clip_content}")
        if not llm_output or llm_output == "llm failed":
            llm_output = ""

        candidate = _unwrap_fenced(llm_output).strip().lower()

        # Convert candidate into safe hyphen-joined branch name (keep letters/numbers)
        words = re.findall(r"[a-z0-9]+", candidate)

        # If LLM didn't produce usable tokens, fall back to extracting from input
        if not words:
            words = re.findall(r"[a-z0-9]+", clip_content.lower())

        if not words:
            return make_alfred_output("", {MESSAGE: "Could not derive branch name", MESSAGE_TITLE: "Error"})

        branch_parts = words[:2]
        branch_name = "-".join(branch_parts)

        # Trim long names
        if len(branch_name) > 50:
            branch_name = branch_name[:50].rstrip("-")

        return make_alfred_output(branch_name, {MESSAGE: "Branch name generated!", MESSAGE_TITLE: "Success"})
    except Exception as e:
        return make_alfred_output("", {MESSAGE: f"LLM generation failed: {str(e)}", MESSAGE_TITLE: "Error"})


def diff_hunk_to_file_line(input_text: str) -> str:
    """Parse a unified git diff text and return a single string in the form
    'path:line' where `path` is the file path without the a/ or b/ prefix
    and `line` is the starting line number from the hunk header. The
    function prefers the old-file hunk start (the '-' number). If the old
    start is 0 (e.g. new file), it falls back to the new-file start.

    Example input contains lines like:
      --- a/datafusion/core/src/physical_planner.rs
      +++ b/datafusion/core/src/physical_planner.rs
      @@ -740,18 +740,23 @@

    Returns an empty string when no path can be determined.
    """
    if not input_text:
        return ""

    path = None
    # Prefer the +++ b/... line (the new path) if present and not /dev/null
    for ln in input_text.splitlines():
        m = re.match(r'^\+\+\+\s+[ab]/(.+)', ln)
        if m:
            candidate = m.group(1).strip()
            if candidate and candidate != '/dev/null':
                path = candidate
                break

    # Fall back to --- a/... if +++ wasn't useful
    if not path:
        for ln in input_text.splitlines():
            m = re.match(r'^---\s+[ab]/(.+)', ln)
            if m:
                candidate = m.group(1).strip()
                if candidate and candidate != '/dev/null':
                    path = candidate
                    break

    if not path:
        return ""

    # Find the first @@ hunk header and extract the old/new start numbers
    for ln in input_text.splitlines():
        m = re.match(r'^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@', ln)
        if m:
            try:
                old_start = int(m.group(1))
            except Exception:
                old_start = 0
            try:
                new_start = int(m.group(3))
            except Exception:
                new_start = 0

            # Prefer old_start if it's a positive non-zero value, otherwise use new_start
            line_no = old_start if old_start and old_start != 0 else new_start
            if not line_no:
                line_no = 1
            return f"{path}:{line_no}"

    # No hunk header found — default to line 1
    return f"{path}:1"


def rewrite_github_blob_for_pr_branch(url: str, pr_branch: str) -> str:
    """Rewrite a GitHub blob/tree URL to use the owner and branch from pr_branch.

    pr_branch is expected in the form 'owner:branch'. If owner is omitted
    (no ':' found), only the branch will be replaced. The function supports
    both 'blob' and 'tree' URL segments and preserves the rest of the path
    and any fragment (e.g. line anchors).

    Examples:
        url = 'https://github.com/kosiew/datafusion/blob/test/path/file.rs#L1'
        pr_branch = 'Jefffrey:acc_args_input_fields'
        -> 'https://github.com/Jefffrey/datafusion/blob/acc_args_input_fields/path/file.rs#L1'
    """
    if not url:
        return url

    # Parse pr_branch into owner and branch
    owner = None
    branch = pr_branch or ""
    if pr_branch and ":" in pr_branch:
        owner, branch = pr_branch.split(":", 1)

    # Regex to capture: scheme+host, owner, repo, (blob|tree), branch, optional path, optional fragment
    m = re.match(r"^(https://github\.com/)([^/]+)/([^/]+)/(blob|tree)/([^/]+)(/[^#]*)?(#.*)?$", url)
    if not m:
        # Not a recognized GitHub blob/tree URL; return original
        return url

    scheme_host = m.group(1)
    orig_owner = m.group(2)
    repo = m.group(3)
    kind = m.group(4)
    _orig_branch = m.group(5)
    path = m.group(6) or ""
    fragment = m.group(7) or ""

    new_owner = owner if owner else orig_owner
    new_branch = branch if branch else _orig_branch

    return f"{scheme_host}{new_owner}/{repo}/{kind}/{new_branch}{path}{fragment}"


def open_clipboard_vscode_link(clip_content: str):
    """Extract a VS Code link from clipboard content and open it.
    
    Looks for VS Code links in the format: vscode://file/path/to/file:line
    or similar patterns found in diff hunks like the example:
    vscode://file//Users/kosiew/GitHub/datafusion/datafusion/catalog/src/table.rs:80
    
    Returns a dict with Alfred output containing success/error messages.
    """
    if not clip_content:
        return make_alfred_output("", {MESSAGE: "Clipboard is empty", MESSAGE_TITLE: "Error"})
    
    # Regex to find VS Code links in the format: vscode://file/path/to/file:line
    vscode_regex = re.compile(r"vscode://file/([^:\s]+)(?::(\d+))?", re.IGNORECASE)
    match = vscode_regex.search(clip_content)
    
    if not match:
        return make_alfred_output("", {MESSAGE: "No VS Code link found in clipboard", MESSAGE_TITLE: "Error"})
    
    file_path = match.group(1)
    line_number = match.group(2) or "1"
    
    try:
        # Open the file in VS Code using the vscode:// protocol
        # Format: vscode://file/path/to/file:line:column
        vscode_link = f"vscode://file/{file_path}:{line_number}"
        subprocess.run(["open", vscode_link], check=True)
        
        return make_alfred_output(
            vscode_link,
            {MESSAGE: f"Opened {file_path}:{line_number}", MESSAGE_TITLE: "Success"}
        )
    except Exception as e:
        return make_alfred_output(
            "",
            {MESSAGE: f"Failed to open VS Code link: {str(e)}", MESSAGE_TITLE: "Error"}
        )


def do():
    """Main function to handle Alfred workflow input and output."""
    action = sys.argv[1]
    output = {}
    if action == "new_dictionary_entry":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Process the text
        word, meaning = process_text(input_text)

        # Prepare JSON output for Alfred
        output = make_alfred_output(word, {MESSAGE: "Transformed text copied!", MESSAGE_TITLE: "Success", WORD: word, MEANING: meaning})

    if action == "parse_whatsapp_number":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Extract phone number
        # keep + at the beginning and digits only
        phone_number = re.sub(r"\D", "", input_text)
        if not phone_number.startswith("+"):
            phone_number = "+6" + phone_number

        # Prepare JSON output for Alfred
        output = make_alfred_output(phone_number, {MESSAGE: "Phone number copied!", MESSAGE_TITLE: phone_number, WHATSAPP_NUMBER: phone_number})

    elif action == "streamline_use_in_rust":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Streamline the Rust import statements
        streamlined_text = streamline_rust_imports(input_text)

        # Prepare JSON output for Alfred
        output = make_alfred_output(streamlined_text, {MESSAGE: "Streamlined imports copied!", MESSAGE_TITLE: "Success"})
        
    elif action == "streamline_use_in_rust_high":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Streamline the Rust import statements
        streamlined_text = streamline_rust_imports_high(input_text)

        # Prepare JSON output for Alfred
        output = make_alfred_output(streamlined_text, {MESSAGE: "Streamlined imports copied!", MESSAGE_TITLE: "Success"})
        
    elif action == "streamline_use_in_rust_low":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Streamline the Rust import statements
        streamlined_text = streamline_rust_imports_low(input_text)

        # Prepare JSON output for Alfred
        output = make_alfred_output(streamlined_text, {MESSAGE: "Streamlined imports copied!", MESSAGE_TITLE: "Success"})

    elif action == "streamline_import_in_python":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Streamline the Python import statements
        streamlined_text = streamline_python_imports(input_text)

        # Prepare JSON output for Alfred
        output = make_alfred_output(streamlined_text, {MESSAGE: "Streamlined imports copied!", MESSAGE_TITLE: "Success"})

    elif action == "remove_println_in_rust":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Remove debug println statements
        filtered_text = remove_rust_printlns(input_text)

        # Prepare JSON output for Alfred
        output = make_alfred_output(filtered_text, {MESSAGE: "Debug printlns removed!", MESSAGE_TITLE: "Success"})

    elif action == "remove_print_in_python":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Remove debug print statements
        filtered_text = remove_python_prints(input_text)

        # Prepare JSON output for Alfred
        output = make_alfred_output(filtered_text, {MESSAGE: "Debug prints removed!", MESSAGE_TITLE: "Success"})

    elif action == "remove_metadata":
        # Get image path from Alfred environment variable
        image_path = os.getenv("entry", "").strip()

        # Strip metadata from the image
        success, message = strip_metadata(image_path)

        # Prepare JSON output for Alfred
        output = make_alfred_output(image_path if success else message, {MESSAGE: message, MESSAGE_TITLE: "Success" if success else "Error"})

    elif action == "rename_dalle_file":  # newly added action branch= "__main__":
        output = rename_dalle_files()
        
    elif action == "check_string_match":
        # Get input text and search string from Alfred environment variables
        input_text = os.getenv("entry", "").strip()
        search_string = os.getenv("search_string", "").strip()

        result = check_string_match(input_text, search_string)

        # Prepare JSON output for Alfred
        output = make_alfred_output(result, {MESSAGE: f"{result} - '{search_string}' in input", MESSAGE_TITLE: "Check String Match"})
        
    elif action == "substitute_search_string":
        # Get input text and search string from Alfred environment variables
        input_text = os.getenv("entry", "").strip()
        search_string = os.getenv("search_string", "").strip()
        replace_with = sys.argv[2]

        # Replace all occurrences of search_string with replace_with
        result_text = input_text.replace(search_string, replace_with)

        # Prepare JSON output for Alfred
        output = make_alfred_output(result_text, {MESSAGE: f"Replaced '{search_string}' with '{replace_with}'", MESSAGE_TITLE: "String Substitution"})

    elif action == "remove_plus_prefix":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Remove plus prefix from lines
        filtered_text = remove_plus_prefix(input_text)

        # Prepare JSON output for Alfred
        output = make_alfred_output(filtered_text, {MESSAGE: "Plus/minus prefixes removed!", MESSAGE_TITLE: "Success"})

    elif action == "show_diffed_result":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").rstrip()

        # Process the diffed result
        processed_text = show_diffed_result(input_text)

        # Prepare JSON output for Alfred
        output = make_alfred_output(processed_text, {MESSAGE: "Diffed result shown!", MESSAGE_TITLE: "Success"})
    elif action == "show_reverse_diffed_result":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").rstrip()

        # Process the diffed result
        processed_text = show_reverse_diffed_result(input_text)

        # Prepare JSON output for Alfred
        output = make_alfred_output(processed_text, {MESSAGE: "Diffed result shown!", MESSAGE_TITLE: "Success"})

    elif action == "html_to_markdown":
        # Get input HTML from Alfred environment variable
        input_html = os.getenv("entry", "").strip()

        # Convert HTML to markdown
        markdown_text = html_to_markdown(input_html)

        # Prepare JSON output for Alfred
        output = make_alfred_output(markdown_text, {MESSAGE: "HTML converted to markdown!", MESSAGE_TITLE: "Success"})

    elif action == "remove_spaces":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Remove all spaces from the text
        processed_text = remove_spaces(input_text)

        # Prepare JSON output for Alfred
        output = make_alfred_output(processed_text, {MESSAGE: "Spaces removed!", MESSAGE_TITLE: "Success"})

    elif action == "clip_to_commit":
        # Get clipboard content from Alfred environment variable
        clip_content = os.getenv("entry", "").strip()
        # Delegate to helper which returns the Alfred JSON output
        output = generate_commit_message_from_clip(clip_content)
        
    elif action == "clip_to_branch":
        # Get clipboard content from Alfred environment variable
        clip_content = os.getenv("entry", "").strip()
        # Delegate to helper which returns the Alfred JSON output with branch name
        output = generate_branch_name_from_clip(clip_content)

    elif action == "commit_range":
        # Get clipboard content from Alfred environment variable
        clip_content = os.getenv("entry", "").strip()
        output = generate_commit_range_from_clip(clip_content)

    elif action == "rewrite_github_blob_for_pr":
        # Read URL and PR branch from environment variables
        input_url = os.getenv("entry", "").strip()
        pr_branch = os.getenv("pr_branch", "").strip()

        # Perform rewrite
        rewritten = rewrite_github_blob_for_pr_branch(input_url, pr_branch)

        # Prepare JSON output for Alfred
        output = make_alfred_output(rewritten, {MESSAGE: "URL rewritten", MESSAGE_TITLE: "Success"})

    elif action == "diff_hunk_to_file_line":
        # Read unified diff text from Alfred environment variable 'entry'
        input_text = os.getenv("entry", "").strip()

        # Parse and produce path:line
        result = diff_hunk_to_file_line(input_text)

        output = make_alfred_output(result, {MESSAGE: "Path:Line extracted", MESSAGE_TITLE: "Success"})

    elif action == "open_clipboard_vscode_link":
        # Get clipboard content from Alfred environment variable
        clip_content = os.getenv("entry", "").strip()
        # Extract VS Code link and open it
        output = open_clipboard_vscode_link(clip_content)

    
    output_json(output)
if __name__ == "__main__":    do()# github repo alfred-workflows