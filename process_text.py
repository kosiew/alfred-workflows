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

def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    kw.setdefault("check", True)
    kw.setdefault("text", True)
    kw.setdefault("capture_output", True)
    return subprocess.run(cmd, **kw)

def _llm(flags: list[str], prompt: str, input_text: Optional[str] = None) -> str:
    """Call llm CLI tool with the given flags and prompt.
    
    Returns the stdout output, or raises an exception if the command fails.
    """
    # Build command exactly like the working shorten function
    cmd = ["llm", *flags, prompt]
    
    proc = subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
        check=True,
    )
    
    return proc.stdout or "ARGH"

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
from rust_import_helpers import (
    process_import_with_braces,
    collect_root_groups,
    highest_common_subpath,
    format_high_group,
    collect_low_groups,
)

def streamline_rust_imports(text):
    return streamline_rust_imports_high(text)

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

    elif action == "html_to_markdown":
        # Get input HTML from Alfred environment variable
        input_html = os.getenv("entry", "").strip()

        # Convert HTML to markdown
        markdown_text = html_to_markdown(input_html)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: markdown_text,
                VARIABLES: {
                    MESSAGE: "HTML converted to markdown!",
                    MESSAGE_TITLE: "Success",
                },
            }
        }

    elif action == "remove_spaces":
        # Get input text from Alfred environment variable
        input_text = os.getenv("entry", "").strip()

        # Remove all spaces from the text
        processed_text = remove_spaces(input_text)

        # Prepare JSON output for Alfred
        output = {
            ALFREDWORKFLOW: {
                ARG: processed_text,
                VARIABLES: {
                    MESSAGE: "Spaces removed!",
                    MESSAGE_TITLE: "Success",
                },
            }
        }

    elif action == "clip_to_commit":
        # Get clipboard content from Alfred environment variable
        clip_content = os.getenv("entry", "").strip()

        if not clip_content:
            output = {
                ALFREDWORKFLOW: {
                    ARG: "",
                    VARIABLES: {
                        MESSAGE: "Clipboard is empty",
                        MESSAGE_TITLE: "Error",
                    },
                }
            }
        else:
            # Generate commit message using llm
            prompt = (
                "Generate a git commit message: one-line subject (imperative, max 50 chars), "
                "blank line, then a short body wrapped at ~72 chars. Do not include code fences."
            )
            
            try:
                # Call llm without -s flag (like the working shorten function)
                llm_output = _llm([], prompt, input_text=clip_content)
                
                if not llm_output:
                    output = {
                        ALFREDWORKFLOW: {
                            ARG: "",
                            VARIABLES: {
                                MESSAGE: "LLM returned empty output",
                                MESSAGE_TITLE: "Error",
                            },
                        }
                    }
                else:
                    commit_msg = _unwrap_fenced(llm_output).strip()
                    
                    if not commit_msg:
                        output = {
                            ALFREDWORKFLOW: {
                                ARG: llm_output,  # Return raw output for debugging
                                VARIABLES: {
                                    MESSAGE: "LLM output was empty after unwrapping",
                                    MESSAGE_TITLE: "Error",
                                },
                            }
                        }
                    else:
                        output = {
                            ALFREDWORKFLOW: {
                                ARG: commit_msg,
                                VARIABLES: {
                                    MESSAGE: "Commit message generated!",
                                    MESSAGE_TITLE: "Success",
                                },
                            }
                        }
            except subprocess.CalledProcessError as e:
                output = {
                    ALFREDWORKFLOW: {
                        ARG: "",
                        VARIABLES: {
                            MESSAGE: f"llm command failed: {e.stderr or e.stdout or str(e)}",
                            MESSAGE_TITLE: "Error",
                        },
                    }
                }
            except FileNotFoundError:
                output = {
                    ALFREDWORKFLOW: {
                        ARG: "",
                        VARIABLES: {
                            MESSAGE: "llm command not found in PATH",
                            MESSAGE_TITLE: "Error",
                        },
                    }
                }
            except Exception as e:
                output = {
                    ALFREDWORKFLOW: {
                        ARG: "",
                        VARIABLES: {
                            MESSAGE: f"Error: {type(e).__name__}: {str(e)}",
                            MESSAGE_TITLE: "Error",
                        },
                    }
                }

    output_json(output)
if __name__ == "__main__":    do()# github repo alfred-workflows