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
    use_statements = []
    other_lines = []
    
    # Separate "use" statements from other lines
    for line in lines:
        line = line.strip()
        if line.startswith('use ') and line.endswith(';'):
            use_statements.append(line)
        else:
            other_lines.append(line)
    
    # Parse and group imports by base path
    grouped_imports = {}
    special_imports = []
    
    for statement in use_statements:
        # Remove 'use ' prefix and ';' suffix
        import_path = statement[4:-1].strip()
        
        # Handle special cases like "use super::*"
        if not '::' in import_path or import_path.endswith('::*'):
            special_imports.append(statement)
            continue
        
        # Find the right-most "::" that isn't inside braces
        parts = import_path.split('::')
        
        # Simple heuristic: check if the last part starts with a brace
        if parts[-1].startswith('{'):
            # It's already a grouped import
            base_path = '::'.join(parts[:-1])
            items_str = parts[-1][1:-1]  # Remove { }
            items = [item.strip() for item in items_str.split(',')]
        else:
            # It's a simple import
            last_part = parts[-1]
            base_path = '::'.join(parts[:-1])
            items = [last_part]
        
        if base_path not in grouped_imports:
            grouped_imports[base_path] = []
        
        # Add items without duplicates
        for item in items:
            if item and item not in grouped_imports[base_path]:
                grouped_imports[base_path].append(item)
    
    # Generate streamlined imports
    streamlined_imports = []
    
    # Add special imports first
    streamlined_imports.extend(special_imports)
    
    # Add consolidated imports
    for base_path, items in sorted(grouped_imports.items()):
        sorted_items = sorted(items)
        if len(sorted_items) == 1:
            streamlined_imports.append(f'use {base_path}::{sorted_items[0]};')
        else:
            items_str = ', '.join(sorted_items)
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

    elif action == "rename_dalle_file":  # newly added action branch
        output = rename_dalle_files()

    output_json(output)


if __name__ == "__main__":
    do()

# github repo alfred-workflows
