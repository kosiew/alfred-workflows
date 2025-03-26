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
        
        all_recent = [f for f in downloads_dir.iterdir() if f.stat().st_mtime > few_min_ago]
        
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
    clean_output = " ".join(words[-number_of_words:]).replace('"', '').replace("'", "")
    
    return clean_output


def streamline_rust_imports(text):
    """Streamlines Rust import statements by consolidating imports with the same base path."""
    if not text or text.isspace():
        return text
    
    lines = text.strip().split('\n')
    
    # Process lines to capture cfg attributes with their use statements
    use_statements = []  # Will contain (cfg_attr, use_statement) tuples
    other_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if this is a cfg attribute that might be attached to a use statement
        if line.startswith('#[cfg') and i + 1 < len(lines) and lines[i + 1].strip().startswith('use '):
            cfg_attr = line
            use_stmt = lines[i + 1].strip()
            if use_stmt.endswith(';'):
                use_statements.append((cfg_attr, use_stmt))
                i += 2  # Skip both the attribute and the use statement
                continue
        
        # Regular use statement without attribute
        elif line.startswith('use ') and line.endswith(';'):
            use_statements.append((None, line))  # No cfg attribute
        else:
            other_lines.append(line)
        
        i += 1
    
    # Parse and group imports by base path, preserving cfg attributes
    grouped_imports = {}  # {base_path: [(cfg_attr, items)]}
    special_imports = []  # [(cfg_attr, statement)]
    
    for cfg_attr, statement in use_statements:
        # Remove 'use ' prefix and ';' suffix
        import_path = statement[4:-1].strip()
        
        # Handle special cases like "use super::*"
        if not '::' in import_path or import_path.endswith('::*'):
            special_imports.append((cfg_attr, statement))
            continue
        
        # Extract base path (everything before the last :: that's not inside braces)
        in_brace = False
        base_path = ""
        remainder = ""
        
        # Find the last :: that's not inside braces
        brace_count = 0
        for i, char in enumerate(import_path):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            elif char == ':' and i + 1 < len(import_path) and import_path[i+1] == ':' and brace_count == 0:
                base_path = import_path[:i]
                remainder = import_path[i+2:]  # Skip the ::
                i += 1  # Skip the next char as we've processed it
            
        # If we couldn't parse properly, treat as special
        if not base_path:
            special_imports.append((cfg_attr, statement))
            continue
        
        # Process the items part
        items = []
        if remainder.startswith('{') and remainder.endswith('}'):
            # It's a grouped import
            items_str = remainder[1:-1]  # Remove { }
            # Split by comma but respect nested braces
            depth = 0
            current_item = ""
            for char in items_str + ',':  # Add comma to handle the last item
                if char == '{':
                    depth += 1
                    current_item += char
                elif char == '}':
                    depth -= 1
                    current_item += char
                elif char == ',' and depth == 0:
                    items.append(current_item.strip())
                    current_item = ""
                else:
                    current_item += char
        else:
            # It's a simple import
            items = [remainder]
        
        if base_path not in grouped_imports:
            grouped_imports[base_path] = []
        
        # Add items with their cfg attribute (if any)
        for item in items:
            if item:
                # Check if this item already exists
                exists = False
                for existing_cfg, existing_items in grouped_imports[base_path]:
                    if item in existing_items and existing_cfg == cfg_attr:
                        exists = True
                        break
                
                if not exists:
                    # Find or create appropriate cfg group
                    group_found = False
                    for i, (existing_cfg, existing_items) in enumerate(grouped_imports[base_path]):
                        if existing_cfg == cfg_attr:
                            grouped_imports[base_path][i][1].append(item)
                            group_found = True
                            break
                    
                    if not group_found:
                        # No matching cfg group found, create new one
                        grouped_imports[base_path].append([cfg_attr, [item]])
    
    # Generate streamlined imports
    streamlined_imports = []
    
    # Add special imports first, with their cfg attributes if any
    for cfg_attr, statement in special_imports:
        if cfg_attr:
            streamlined_imports.append(cfg_attr)
        streamlined_imports.append(statement)
    
    # Add consolidated imports with their cfg attributes
    for base_path, cfg_groups in sorted(grouped_imports.items()):
        for cfg_attr, items in cfg_groups:
            sorted_items = sorted(items)
            if len(sorted_items) == 1:
                if cfg_attr:
                    streamlined_imports.append(cfg_attr)
                streamlined_imports.append(f'use {base_path}::{sorted_items[0]};')
            else:
                items_str = ', '.join(sorted_items)
                if cfg_attr:
                    streamlined_imports.append(cfg_attr)
                streamlined_imports.append(f'use {base_path}::{{{items_str}}};')
    
    # Combine result
    result = other_lines + streamlined_imports
    return '\n'.join(result)


def streamline_python_imports(text):
    """Streamlines Python import statements by consolidating imports from the same module."""
    if not text or text.isspace():
        return text
    
    lines = text.strip().split('\n')
    
    # Group imports by module
    simple_imports = set()  # For "import x"
    from_imports = {}  # For "from x import y"
    
    for line in lines:
        line = line.strip()
        
        # Handle "import x" statements
        if line.startswith('import ') and not 'from ' in line:
            modules = [m.strip() for m in line[7:].split(',')]
            for module in modules:
                simple_imports.add(module)
                
        # Handle "from x import y" statements
        elif line.startswith('from '):
            parts = line.split(' import ')
            if len(parts) == 2:
                module = parts[0][5:].strip()
                items = [item.strip() for item in parts[1].split(',')]
                
                if module not in from_imports:
                    from_imports[module] = []
                
                for item in items:
                    if item and item not in from_imports[module]:
                        from_imports[module].append(item)
    
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
        if len(', '.join(sorted_items)) > 79:
            result.append(f"from {module} import (")
            for item in sorted_items:
                result.append(f"    {item},")
            result.append(")")
        else:
            items_str = ', '.join(sorted_items)
            result.append(f"from {module} import {items_str}")
    
    return '\n'.join(result)


def remove_rust_printlns(text):
    """Removes println!("==> ...") statements from Rust code, including multi-line ones."""
    if not text or text.isspace():
        return text
    
    # Split into lines and add a line index
    lines = text.strip().split('\n')
    filtered_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line starts a debug println
        if 'println!' in line and ('==> ' in line or (line.strip().endswith('println!(') and i + 1 < len(lines) and '==> ' in lines[i+1])):
            # Found a debug println, now find where it ends
            j = i
            
            # Continue until we find the closing pattern ");", accounting for possible strings containing ");"
            while ');' not in lines[j]:
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
    
    return '\n'.join(filtered_lines)


def remove_python_prints(text):
    """Removes print("==> ...") or print('==> ...') statements from Python code, including multi-line ones."""
    if not text or text.isspace():
        return text
    
    lines = text.strip().split('\n')
    filtered_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line starts a debug print statement (with single or double quotes)
        if 'print(' in line and ('"==> ' in line or "'==> " in line or 
                                (line.strip().endswith('print(') and i + 1 < len(lines) and 
                                 ('"==> ' in lines[i+1] or "'==> " in lines[i+1]))):
            # Found a debug print, now find where it ends
            j = i
            
            # Continue until we find the closing parenthesis
            while ')' not in lines[j]:
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
    
    return '\n'.join(filtered_lines)

def strip_metadata(image_path):
    """
    Strips all metadata, including C2PA, from the given image file using exiftool.
    """
    if not os.path.exists(image_path):
        return False, f"File not found: {image_path}"

    try:
        # Remove metadata and overwrite the original image
        subprocess.run(['exiftool', '-all=', '-overwrite_original', image_path], check=True)
        return True, f"Metadata stripped from {image_path}"
    except subprocess.CalledProcessError as e:
        return False, f"Error while stripping metadata: {e}"
    except FileNotFoundError:
        return False, "Error: exiftool not installed. Install with 'brew install exiftool'"

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

    elif action == "rename_dalle_file":  # newly added action branch
        output = rename_dalle_files()

    output_json(output)


if __name__ == "__main__":
    do()

# github repo alfred-workflows
