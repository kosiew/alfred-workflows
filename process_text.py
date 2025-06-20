import sys
import re
import json
import os
import subprocess  # newly added
from pathlib import Path  # newly added
import time  # newly added

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



def parse_python_import_statements(lines):
    """
    Parse Python import statements from the input lines.
    
    Args:
        lines: List of text lines containing import statements
    
    Returns:
        tuple: (simple_imports, from_imports)
            - simple_imports: Set of simple imports ("import x")
            - from_imports: Dict mapping module names to lists of imported items
    """
    simple_imports = set()  # For "import x"
    from_imports = {}  # For "from x import y"

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Handle "import x" statements
        if line.startswith("import ") and "from " not in line:
            modules = [m.strip() for m in line[7:].split(",")]
            for module in modules:
                simple_imports.add(module)
            i += 1

        # Handle "from x import y" statements
        elif line.startswith("from "):
            # Check if this is a multi-line parenthesized import
            if "(" in line and ")" not in line:
                module, items = parse_multiline_from_import(lines, i)
                
                # Add to from_imports
                add_from_imports(from_imports, module, items)
                
                # Update index to skip processed lines
                i += count_lines_until_closing_paren(lines, i)
            else:
                # Regular single-line import
                module, items = parse_single_line_from_import(line)
                if module and items:
                    add_from_imports(from_imports, module, items)
                i += 1
        else:
            i += 1  # Skip non-import lines

    return simple_imports, from_imports


def parse_multiline_from_import(lines, start_idx):
    """
    Parse a multi-line from-import statement.
    
    Args:
        lines: List of text lines
        start_idx: Starting index of the import statement
    
    Returns:
        tuple: (module, items)
            - module: The module being imported from
            - items: List of imported items
    """
    line = lines[start_idx].strip()
    
    # Extract module name
    module = line.split(" import ")[0][5:].strip()
    
    # Collect all items until closing parenthesis
    items = []
    idx = start_idx + 1  # Move to the next line
    
    while idx < len(lines) and ")" not in lines[idx]:
        item_line = lines[idx].strip()
        if item_line and not item_line.startswith("#"):  # Skip comments
            # Remove trailing commas and whitespace
            item = item_line.rstrip(",").strip()
            if item:
                items.append(item)
        idx += 1
    
    # Process the line with closing parenthesis
    if idx < len(lines):
        item_line = lines[idx].strip()
        # Check if there's an item before the closing parenthesis
        if item_line != ")":
            item = item_line.rstrip(",").rstrip(")").strip()
            if item and item != ")":
                items.append(item)
    
    return module, items


def count_lines_until_closing_paren(lines, start_idx):
    """
    Count lines until we find a closing parenthesis.
    
    Args:
        lines: List of text lines
        start_idx: Starting index
    
    Returns:
        int: Number of lines to skip
    """
    count = 1  # Start from the next line
    idx = start_idx + 1
    
    while idx < len(lines) and ")" not in lines[idx]:
        count += 1
        idx += 1
    
    # Include the line with closing parenthesis
    if idx < len(lines):
        count += 1
        
    return count


def parse_single_line_from_import(line):
    """
    Parse a single-line from-import statement.
    
    Args:
        line: Line of text containing the import statement
    
    Returns:
        tuple: (module, items)
            - module: The module being imported from
            - items: List of imported items
    """
    parts = line.split(" import ")
    if len(parts) != 2:
        return None, []
        
    module = parts[0][5:].strip()  # Remove 'from ' prefix
    
    # Handle both normal and parenthesized single-line imports
    items_part = parts[1].strip()
    if items_part.startswith("(") and items_part.endswith(")"):
        items_part = items_part[1:-1]  # Remove parentheses
    
    items = [item.strip() for item in items_part.split(",")]
    return module, [item for item in items if item]


def add_from_imports(from_imports, module, items):
    """
    Add items to the from_imports dictionary.
    
    Args:
        from_imports: Dictionary of from-imports
        module: Module name
        items: List of items to import
    """
    if module not in from_imports:
        from_imports[module] = []
    
    for item in items:
        if item and item not in from_imports[module]:
            from_imports[module].append(item)


def generate_python_import_statements(simple_imports, from_imports):
    """
    Generate consolidated import statements.
    
    Args:
        simple_imports: Set of simple imports
        from_imports: Dict mapping module names to lists of imported items
    
    Returns:
        list: List of consolidated import statements
    """
    result = []

    # Simple imports
    if simple_imports:
        sorted_imports = sorted(simple_imports)
        for module in sorted_imports:
            result.append(f"import {module}")

    # From imports
    for module, items in sorted(from_imports.items()):
        sorted_items = sorted(items)
        # If many items, use multi-line format
        if len(", ".join(sorted_items)) > 79:
            result.append(f"from {module} import (")
            for item in sorted_items:
                result.append(f"    {item},")
            result.append(")")
        else:
            items_str = ", ".join(sorted_items)
            result.append(f"from {module} import {items_str}")

    return result


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

    output_json(output)
if __name__ == "__main__":    do()# github repo alfred-workflows