import sys
import re
import json
import os
import subprocess  # newly added
from pathlib import Path  # newly added
import time  # newly added
from python_import_helpers import parse_python_import_statements, generate_python_import_statements

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

        output = {
            ALFREDWORKFLOW: {
                ARG: short_name,
                VARIABLES: {
                    MESSAGE: f"Renamed → {short_name}",
                    MESSAGE_TITLE: "Rename Success",
                },
            }
        }
    except Exception as e:
        output = {
            ALFREDWORKFLOW: {
                ARG: str(e),
                VARIABLES: {MESSAGE: f"Error: {e}", MESSAGE_TITLE: "Rename Failed"},
            }
        }

    return output


def shorten(phrase, number_of_words=2):
    result = subprocess.run(
        ["llm", "-m", "l32", f"shorten to {number_of_words} meaningful unique word"],
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
from rust_import_helpers import process_import_with_braces

def streamline_rust_imports(text):
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

    # Build a mapping of root -> ordered list of (subpath -> set(items))
    root_groups = {}  # root -> { (is_pub, attr_key): { subpath_order: [subpaths], submap: {subpath: set(items)} } }
    special_imports = []

    for cfg_attr, statement, is_pub in use_statements:
        prefix_len = 8 if is_pub else 4
        import_path = statement[prefix_len:-1].strip()

        if "::" not in import_path or import_path.endswith("::*"):
            special_imports.append((cfg_attr, statement, is_pub))
            continue

        # Determine base path and items
        if "{" in import_path:
            mapping = process_import_with_braces(import_path)
            # mapping: base_path -> set(items)
            for base_path, items in mapping.items():
                parts = [p for p in base_path.split("::") if p]
                root = parts[0]
                subpath = "::".join(parts[1:]) if len(parts) > 1 else ""

                key = (root, is_pub)
                if key not in root_groups:
                    root_groups[key] = {"order": [], "submap": {}, "attrs": {}}

                # preserve subpath order of first occurrence
                if subpath not in root_groups[key]["submap"]:
                    root_groups[key]["order"].append(subpath)
                    root_groups[key]["submap"][subpath] = set()

                root_groups[key]["submap"][subpath].update(items)
        else:
            parts = [p for p in import_path.split("::") if p]
            root = parts[0]
            subpath = "::".join(parts[1:-1]) if len(parts) > 2 else parts[1] if len(parts) > 1 else ""
            item = parts[-1]

            key = (root, is_pub)
            if key not in root_groups:
                root_groups[key] = {"order": [], "submap": {}, "attrs": {}}

            if subpath not in root_groups[key]["submap"]:
                root_groups[key]["order"].append(subpath)
                root_groups[key]["submap"][subpath] = set()

            root_groups[key]["submap"][subpath].add(item)

    # Generate result lines
    result = []

    # Emit special imports first (unchanged)
    for cfg_attr, stmt, _ in special_imports:
        if cfg_attr:
            result.append(cfg_attr)
        result.append(stmt)

    # For each root (preserve deterministic order by sorted root name)
    for (root, is_pub) in sorted(root_groups.keys()):
        group = root_groups[(root, is_pub)]
        prefix = "pub use " if is_pub else "use "

        # Determine highest common subpath among all subpaths in this root
        subpaths = [s for s in group["submap"].keys() if s is not None]
        # Filter out empty subpaths
        nonempty = [s for s in subpaths if s]

        common_sub = ""
        if nonempty:
            # Split each subpath into parts
            split_lists = [s.split("::") for s in nonempty]
            # Find common prefix
            common = []
            for parts in zip(*split_lists):
                if all(p == parts[0] for p in parts):
                    common.append(parts[0])
                else:
                    break
            if common:
                common_sub = "::".join(common)

        # If we have a non-empty common_sub, collapse into that path, otherwise use root grouping
        if common_sub:
            # collect everything under common_sub
            inner_map = {}
            for sub, items in group["submap"].items():
                # if sub starts with common_sub, map the remainder; if sub == common_sub, remainder is ''
                if sub == "":
                    remainder = ""
                elif sub.startswith(common_sub):
                    remainder = sub[len(common_sub)+2:] if len(sub) > len(common_sub) else ""
                else:
                    # this shouldn't happen for common_sub calculation, but treat as top-level remainder
                    remainder = sub

                inner_map.setdefault(remainder, set()).update(items)

            # Build entries from inner_map preserving original order where possible
            order = [s for s in group["order"] if s.startswith(common_sub) or s == ""]
            # ensure uniqueness
            seen = set()
            ordered_remainders = []
            for s in order:
                if s == "":
                    r = ""
                elif s.startswith(common_sub):
                    r = s[len(common_sub)+2:] if len(s) > len(common_sub) else ""
                else:
                    r = s
                if r not in seen:
                    seen.add(r)
                    ordered_remainders.append(r)

            # Format entries
            result.append(f"{prefix}{root}::{common_sub}::{{")
            for rem in ordered_remainders:
                items = inner_map.get(rem, set())
                lower_items = sorted([it for it in items if it and it[0].islower()])
                upper_items = sorted([it for it in items if not (it and it[0].islower())])
                sorted_items = lower_items + upper_items

                if rem == "":
                    if len(sorted_items) == 1:
                        result.append(f"    {sorted_items[0]},")
                    else:
                        result.append(f"    {{{', '.join(sorted_items)}}},")
                else:
                    if len(sorted_items) == 1:
                        result.append(f"    {rem}::{sorted_items[0]},")
                    else:
                        result.append(f"    {rem}::{{{', '.join(sorted_items)}}},")
            result.append("};")
        else:
            # No deeper common subpath — use root::{ ... }
            inner_entries = []
            for sub in group["order"]:
                items = group["submap"][sub]
                lower_items = sorted([it for it in items if it and it[0].islower()])
                upper_items = sorted([it for it in items if not (it and it[0].islower())])
                sorted_items = lower_items + upper_items

                if sub == "":
                    if len(sorted_items) == 1:
                        inner_entries.append(f"{sorted_items[0]}")
                    else:
                        inner_entries.append(f"{{{', '.join(sorted_items)}}}")
                else:
                    if len(sorted_items) == 1:
                        inner_entries.append(f"{sub}::{sorted_items[0]}")
                    else:
                        inner_entries.append(f"{sub}::{{{', '.join(sorted_items)}}}")

            result.append(f"{prefix}{root}::{{")
            for entry in inner_entries:
                result.append(f"    {entry},")
            result.append("};")

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

    grouped_by_base = {}
    special_imports = []

    for cfg_attr, statement, is_pub in use_statements:
        prefix_len = 8 if is_pub else 4
        import_path = statement[prefix_len:-1].strip()

        # Keep as special import if it has no '::' or is a glob
        if "::" not in import_path or import_path.endswith("::*"):
            special_imports.append((cfg_attr, statement, is_pub))
            continue

        # If the import contains braces, expand to base_path -> items mapping
        if "{" in import_path:
            mapping = process_import_with_braces(import_path)
            for base_path, items in mapping.items():
                key = (base_path, is_pub)
                if key not in grouped_by_base:
                    grouped_by_base[key] = {}
                attr_key = cfg_attr or ""
                grouped_by_base[key].setdefault(attr_key, set()).update(items)
        else:
            parts = [p for p in import_path.split("::") if p]
            if len(parts) >= 2:
                base_path = "::".join(parts[:-1])
                item = parts[-1]
            else:
                base_path = parts[0]
                item = parts[-1]

            key = (base_path, is_pub)
            if key not in grouped_by_base:
                grouped_by_base[key] = {}
            attr_key = cfg_attr or ""
            grouped_by_base[key].setdefault(attr_key, set()).add(item)

    result = generate_import_statements(grouped_by_base, special_imports)

    if other_lines and result:
        return "\n".join(other_lines + [""] + result)
    return "\n".join(other_lines + result)








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
        output = {
            ALFREDWORKFLOW: {
                ARG: word,
                VARIABLES: {
                    MESSAGE: "Transformed text copied!",
                    MESSAGE_TITLE: "Success",
                    WORD: word,
                    MEANING: meaning,
                },
            }
        }

    if action == "parse_whatsapp_number":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Extract phone number
        # keep + at the beginning and digits only
        phone_number = re.sub(r"\D", "", input_text)
        if not phone_number.startswith("+"):
            phone_number = "+6" + phone_number

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: phone_number,
                VARIABLES: {
                    MESSAGE: "Phone number copied!",
                    MESSAGE_TITLE: phone_number,
                    WHATSAPP_NUMBER: phone_number,
                },
            }
        }

    elif action == "streamline_use_in_rust":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Streamline the Rust import statements
        streamlined_text = streamline_rust_imports(input_text)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: streamlined_text,
                VARIABLES: {
                    MESSAGE: "Streamlined imports copied!",
                    MESSAGE_TITLE: "Success",
                },
            }
        }
        
    elif action == "streamline_use_in_rust_high":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Streamline the Rust import statements
        streamlined_text = streamline_rust_imports_high(input_text)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: streamlined_text,
                VARIABLES: {
                    MESSAGE: "Streamlined imports copied!",
                    MESSAGE_TITLE: "Success",
                },
            }
        }
        
    elif action == "streamline_use_in_rust_low":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Streamline the Rust import statements
        streamlined_text = streamline_rust_imports_low(input_text)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: streamlined_text,
                VARIABLES: {
                    MESSAGE: "Streamlined imports copied!",
                    MESSAGE_TITLE: "Success",
                },
            }
        }

    elif action == "streamline_import_in_python":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Streamline the Python import statements
        streamlined_text = streamline_python_imports(input_text)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: streamlined_text,
                VARIABLES: {
                    MESSAGE: "Streamlined imports copied!",
                    MESSAGE_TITLE: "Success",
                },
            }
        }

    elif action == "remove_println_in_rust":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Remove debug println statements
        filtered_text = remove_rust_printlns(input_text)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: filtered_text,
                VARIABLES: {
                    MESSAGE: "Debug printlns removed!",
                    MESSAGE_TITLE: "Success",
                },
            }
        }

    elif action == "remove_print_in_python":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Remove debug print statements
        filtered_text = remove_python_prints(input_text)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: filtered_text,
                VARIABLES: {
                    MESSAGE: "Debug prints removed!",
                    MESSAGE_TITLE: "Success",
                },
            }
        }

    elif action == "remove_metadata":
        # Get image path from Alfred environment variable
        image_path = os.getenv("entry", "").strip()

        # Strip metadata from the image
        success, message = strip_metadata(image_path)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: image_path if success else message,
                VARIABLES: {
                    MESSAGE: message,
                    MESSAGE_TITLE: "Success" if success else "Error",
                },
            }
        }

    elif action == "rename_dalle_file":  # newly added action branch= "__main__":
        output = rename_dalle_files()
        
    elif action == "check_string_match":
        # Get input text and search string from Alfred environment variables
        input_text = os.getenv("entry", "").strip()
        search_string = os.getenv("search_string", "").strip()

        result = check_string_match(input_text, search_string)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: result,
                VARIABLES: {
                    MESSAGE: f"{result} - '{search_string}' in input",
                    MESSAGE_TITLE: "Check String Match",
                },
            }
        }
        
    elif action == "substitute_search_string":
        # Get input text and search string from Alfred environment variables
        input_text = os.getenv("entry", "").strip()
        search_string = os.getenv("search_string", "").strip()
        replace_with = sys.argv[2]

        # Replace all occurrences of search_string with replace_with
        result_text = input_text.replace(search_string, replace_with)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: result_text,
                VARIABLES: {
                    MESSAGE: f"Replaced '{search_string}' with '{replace_with}'",
                    MESSAGE_TITLE: "String Substitution",
                },
            }
        }

    elif action == "remove_plus_prefix":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Remove plus prefix from lines
        filtered_text = remove_plus_prefix(input_text)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: filtered_text,
                VARIABLES: {
                    MESSAGE: "Plus/minus prefixes removed!",
                    MESSAGE_TITLE: "Success",
                },
            }
        }

    elif action == "show_diffed_result":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").rstrip()

        # Process the diffed result
        processed_text = show_diffed_result(input_text)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: processed_text,
                VARIABLES: {
                    MESSAGE: "Diffed result shown!",
                    MESSAGE_TITLE: "Success",
                },
            }
        }
    elif action == "show_reverse_diffed_result":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").rstrip()

        # Process the diffed result
        processed_text = show_reverse_diffed_result(input_text)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: processed_text,
                VARIABLES: {
                    MESSAGE: "Diffed result shown!",
                    MESSAGE_TITLE: "Success",
                },
            }
        }

    output_json(output)
if __name__ == "__main__":    do()# github repo alfred-workflows