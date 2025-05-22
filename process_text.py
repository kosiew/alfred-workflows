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


def streamline_rust_imports(text):
    """Streamlines Rust import statements by consolidating imports with the same base path."""
    if not text or text.isspace():
        return text

    lines = text.strip().split('\n')

    # Process lines to capture cfg attributes with their use statements
    use_statements = []  # Will contain (cfg_attr, full_statement, is_pub) tuples
    other_lines = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Handle cfg attributes
        if line.startswith('#[cfg') and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            is_pub = next_line.startswith('pub use ')
            is_use = next_line.startswith('use ')

            if (is_pub or is_use) and next_line.endswith(';'):
                use_statements.append((line, next_line, is_pub))
                i += 2
                continue
            elif (is_pub or is_use) and '{' in next_line and not next_line.endswith('};'): 
                # Multi-line import with cfg attribute
                full_statement = next_line
                j = i + 2
                while j < len(lines) and not lines[j].strip().endswith('};'):
                    full_statement += ' ' + lines[j].strip()
                    j += 1
                if j < len(lines):
                    full_statement += ' ' + lines[j].strip()
                    use_statements.append((line, full_statement, is_pub))
                    i = j + 1
                    continue

        # Handle single-line imports
        elif line.startswith('pub use ') and line.endswith(';'):
            use_statements.append((None, line, True))
            i += 1
        elif line.startswith('use ') and line.endswith(';'):
            use_statements.append((None, line, False))
            i += 1
        # Handle multi-line imports
        elif (line.startswith('pub use ') or line.startswith('use ')) and '{' in line and not line.endswith('};'):
            is_pub = line.startswith('pub use ')
            full_statement = line
            j = i + 1
            while j < len(lines) and not lines[j].strip().endswith('};'):
                full_statement += ' ' + lines[j].strip()
                j += 1
            if j < len(lines):
                full_statement += ' ' + lines[j].strip()
                use_statements.append((None, full_statement, is_pub))
                i = j + 1
                continue
            else:
                other_lines.append(line)
                i += 1
        else:
            other_lines.append(line)
            i += 1

    # Dictionary to organize imports by module
    module_imports = {}  # {(module_name, is_pub): {cfg_attr: {nested_path: set(items)}}}
    special_imports = []  # Imports that don't follow the standard pattern

    for cfg_attr, statement, is_pub in use_statements:
        prefix = 'pub use ' if is_pub else 'use '
        
        # Skip malformed statements
        if not (statement.startswith(prefix) and statement.endswith(';')):
            special_imports.append((cfg_attr, statement, is_pub))
            continue
        
        # Extract import path without prefix and trailing semicolon
        import_path = statement[len(prefix):-1].strip()
        
        # Skip special imports like glob imports
        if '::' not in import_path or import_path.endswith('::*'):
            special_imports.append((cfg_attr, statement, is_pub))
            continue
        
        # Extract the root module (e.g., 'std', 'datafusion', etc.)
        parts = import_path.split('::', 1)
        root_module = parts[0]
        
        # Initialize the module entry if needed
        module_key = (root_module, is_pub)
        if module_key not in module_imports:
            module_imports[module_key] = {}
        
        # Initialize the attribute group if needed
        attr_key = cfg_attr or ""
        if attr_key not in module_imports[module_key]:
            module_imports[module_key][attr_key] = {}
        
        # Process the rest of the path after the root module
        if len(parts) > 1 and parts[1].strip():
            rest_of_path = parts[1].strip()
            
            # Handle simple imports like "use std::fmt::Display;"
            if '{' not in rest_of_path:
                subparts = rest_of_path.split('::')
                item = subparts[-1]
                path = '::'.join(subparts[:-1]) if len(subparts) > 1 else ''
                
                if path not in module_imports[module_key][attr_key]:
                    module_imports[module_key][attr_key][path] = set()
                module_imports[module_key][attr_key][path].add(item)
            else:
                # Handle imports with braces like "use std::{fmt::Display, any::Any};"
                # This is a simplified implementation that works for common cases
                
                # For a cleaner implementation, we split the rest of the path at "{"
                before_brace, brace_content = rest_of_path.split('{', 1)
                path_prefix = before_brace.rstrip('::')  # Remove trailing "::" if present
                
                # Remove the closing brace and split by commas
                brace_content = brace_content.rstrip('}')
                
                # Split items by commas, but handle nested braces
                items = []
                current_item = ""
                brace_level = 0
                
                for char in brace_content:
                    if char == '{':
                        brace_level += 1
                        current_item += char
                    elif char == '}':
                        brace_level -= 1
                        current_item += char
                    elif char == ',' and brace_level == 0:
                        items.append(current_item.strip())
                        current_item = ""
                    else:
                        current_item += char
                
                if current_item.strip():
                    items.append(current_item.strip())
                
                # Process each item
                for item in items:
                    if '::' in item:
                        # Item with a path, e.g., "fmt::Display"
                        item_parts = item.split('::', 1)
                        sub_path = item_parts[0]
                        
                        if '{' in item_parts[1]:
                            # Nested brace, e.g., "fmt::{Display, Formatter}"
                            nested_path = path_prefix + ('::' if path_prefix else '') + sub_path
                            nested_content = item_parts[1].strip('{}')
                            nested_items = [i.strip() for i in nested_content.split(',')]
                            
                            if nested_path not in module_imports[module_key][attr_key]:
                                module_imports[module_key][attr_key][nested_path] = set()
                            
                            for nested_item in nested_items:
                                module_imports[module_key][attr_key][nested_path].add(nested_item)
                        else:
                            # Regular path, e.g., "fmt::Display"
                            full_path = path_prefix + ('::' if path_prefix else '') + sub_path
                            sub_item = item_parts[1]
                            
                            if full_path not in module_imports[module_key][attr_key]:
                                module_imports[module_key][attr_key][full_path] = set()
                            
                            module_imports[module_key][attr_key][full_path].add(sub_item)
                    else:
                        # Direct item, e.g., "Any"
                        if path_prefix not in module_imports[module_key][attr_key]:
                            module_imports[module_key][attr_key][path_prefix] = set()
                        
                        module_imports[module_key][attr_key][path_prefix].add(item)

    # Generate the output
    result = []
    
    # Add special imports first
    for cfg_attr, stmt, _ in special_imports:
        if cfg_attr:
            result.append(cfg_attr)
        result.append(stmt)
    
    # Add consolidated imports
    for (module, is_pub), attr_groups in sorted(module_imports.items()):
        for cfg_attr, paths in sorted(attr_groups.items()):
            if cfg_attr:
                result.append(cfg_attr)
            
            prefix = 'pub use ' if is_pub else 'use '
            import_parts = []
            
            for path, items in sorted(paths.items()):
                sorted_items = sorted(items)
                if path:
                    import_parts.append(f"{path}::{{{', '.join(sorted_items)}}}")
                else:
                    import_parts.extend(sorted_items)
            
            result.append(f"{prefix}{module}::{{{', '.join(import_parts)}}};")
    
    if other_lines and result:
        return '\n'.join(other_lines + [''] + result)
    return '\n'.join(other_lines + result)



def streamline_python_imports(text):
    """Streamlines Python import statements by consolidating imports from the same module."""
    if not text or text.isspace():
        return text

    lines = text.strip().split("\n")

    # Group imports by module
    simple_imports = set()  # For "import x"
    from_imports = {}  # For "from x import y"

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Handle "import x" statements
        if line.startswith("import ") and not "from " in line:
            modules = [m.strip() for m in line[7:].split(",")]
            for module in modules:
                simple_imports.add(module)
            i += 1

        # Handle "from x import y" statements
        elif line.startswith("from "):
            # Check if this is a multi-line parenthesized import
            if "(" in line and ")" not in line:
                # Extract module name
                module = line.split(" import ")[0][5:].strip()

                # Collect all items until closing parenthesis
                items = []
                i += 1  # Move to the next line

                while i < len(lines) and ")" not in lines[i]:
                    item_line = lines[i].strip()
                    if item_line and not item_line.startswith("#"):  # Skip comments
                        # Remove trailing commas and whitespace
                        item = item_line.rstrip(",").strip()
                        if item:
                            items.append(item)
                    i += 1

                # Process the line with closing parenthesis
                if i < len(lines):
                    item_line = lines[i].strip()
                    # Check if there's an item before the closing parenthesis
                    if item_line != ")":
                        item = item_line.rstrip(",").rstrip(")").strip()
                        if item and item != ")":
                            items.append(item)
                    i += 1  # Move past the closing parenthesis line

                # Add to from_imports
                if module not in from_imports:
                    from_imports[module] = []
                for item in items:
                    if item and item not in from_imports[module]:
                        from_imports[module].append(item)
            else:
                # Regular single-line import
                parts = line.split(" import ")
                if len(parts) == 2:
                    module = parts[0][5:].strip()
                    # Handle both normal and parenthesized single-line imports
                    items_part = parts[1].strip()
                    if items_part.startswith("(") and items_part.endswith(")"):
                        items_part = items_part[1:-1]  # Remove parentheses

                    items = [item.strip() for item in items_part.split(",")]

                    if module not in from_imports:
                        from_imports[module] = []

                    for item in items:
                        if item and item not in from_imports[module]:
                            from_imports[module].append(item)
                i += 1
        else:
            i += 1  # Skip non-import lines

    # Generate streamlined imports
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

    output_json(output)
if __name__ == "__main__":    do()# github repo alfred-workflows