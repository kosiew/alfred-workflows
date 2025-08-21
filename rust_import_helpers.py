"""Helper functions for processing and streamlining Rust import statements."""

def parse_import_statements(lines):
    """
    Parse Rust import statements from the input lines.
    
    Args:
        lines: List of text lines containing import statements
    
    Returns:
        tuple: (use_statements, other_lines)
            - use_statements: List of (cfg_attr, statement, is_pub) tuples
            - other_lines: List of non-import lines
    """
    # Process lines to capture cfg attributes with their use statements
    use_statements = []  # Will contain (cfg_attr, full_statement, is_pub) tuples
    other_lines = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Handle cfg attributes
        if line.startswith("#[cfg") and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            is_pub = next_line.startswith("pub use ")
            is_use = next_line.startswith("use ")

            if (is_pub or is_use) and next_line.endswith(";"):
                use_statements.append((line, next_line, is_pub))
                i += 2
                continue
            elif (is_pub or is_use) and "{" in next_line and not next_line.endswith("};"): 
                # Multi-line import with cfg attribute
                full_statement = next_line
                j = i + 2
                while j < len(lines) and not lines[j].strip().endswith("};"):
                    full_statement += " " + lines[j].strip()
                    j += 1
                if j < len(lines):
                    full_statement += " " + lines[j].strip()
                    use_statements.append((line, full_statement, is_pub))
                    i = j + 1
                    continue

        # Handle single-line imports
        elif line.startswith("pub use ") and line.endswith(";"):
            use_statements.append((None, line, True))
            i += 1
        elif line.startswith("use ") and line.endswith(";"):
            use_statements.append((None, line, False))
            i += 1
        # Handle multi-line imports
        elif (line.startswith("pub use ") or line.startswith("use ")) and "{" in line and not line.endswith("};"):
            is_pub = line.startswith("pub use ")
            full_statement = line
            j = i + 1
            # Track brace levels to handle nested braces correctly
            brace_count = line.count("{") - line.count("}")
            
            while j < len(lines) and brace_count > 0:
                current_line = lines[j].strip()
                full_statement += " " + current_line
                brace_count += current_line.count("{") - current_line.count("}")
                j += 1
                
                # Break if we've balanced all braces and have a semicolon
                if brace_count == 0 and full_statement.endswith(";"):
                    break
            
            if brace_count == 0 and full_statement.endswith(";"):
                use_statements.append((None, full_statement, is_pub))
                i = j
                continue
            else:
                # If we couldn't properly parse the statement, leave it as-is
                other_lines.append(line)
                i += 1
        else:
            other_lines.append(line)
            i += 1
    
    return use_statements, other_lines


def parse_nested_import_items(items_str):
    """
    Parse import items with nested curly braces.
    
    Args:
        items_str: String containing import items inside curly braces
    
    Returns:
        set: Set of parsed import items
    """
    # Deprecated wrapper retained for backward compatibility.
    # Use the new brace-aware parser which preserves order and provides a 'self' flag.
    items_list, has_self = _parse_brace_aware_items(items_str)
    items_set = set(items_list)
    if has_self:
        items_set.add('self')
    return items_set


def _parse_brace_aware_items(items_str):
    """Parse a brace-aware items string into ordered items and a has_self flag.

    Returns (items_list, has_self) where items_list preserves top-level order and
    items may include nested-brace expressions. This handles nested braces and
    only splits on commas at brace level 0.
    """
    items = []
    current = ""
    brace_level = 0
    has_self = False

    for char in items_str:
        if char == '{':
            brace_level += 1
            current += char
        elif char == '}':
            brace_level -= 1
            current += char
        elif char == ',' and brace_level == 0:
            item = current.strip()
            if item:
                if item == 'self':
                    has_self = True
                else:
                    items.append(item)
            current = ""
        else:
            current += char

    # Final item
    item = current.strip()
    if item:
        if item == 'self':
            has_self = True
        else:
            items.append(item)

    return items, has_self


def _sort_lower_then_upper(items):
    """Return items sorted with lowercase-starting identifiers first, then others."""
    lower_items = sorted([it for it in items if it and it[0].islower()])
    upper_items = sorted([it for it in items if not (it and it[0].islower())])
    return lower_items + upper_items


def process_import_with_braces(import_path):
    """
    Process an import statement with curly braces.
    
    Args:
        import_path: Import path string like 'std::io::{Read, Write}'
    
    Returns:
        tuple: (base_path, items)
            - base_path: Base module path
            - items: Set of import items
    """
    # full_path is the path prefix immediately before the outermost brace
    full_path = import_path[:import_path.index("{")].rstrip("::")
    items_str = import_path[import_path.index("{")+1:-1]

    # Parse nested items into top-level pieces
    items = parse_nested_import_items(items_str)

    # We'll return a mapping: { base_path: set(items) }
    mapping = {}

    def handle_item(prefix, itm):
        itm = itm.strip()
        # If this item itself contains braces, recurse with new prefix
        if "{" in itm:
            mod_name = itm[:itm.index("{")].strip().rstrip(":")
            nested = itm[itm.index("{") + 1 : -1]
            new_prefix = f"{prefix}::" + mod_name if prefix else mod_name
            for sub in parse_nested_import_items(nested):
                handle_item(new_prefix, sub)
        else:
            # If the item contains a ::, split deeper base from the final name
            if "::" in itm:
                parts = [p.strip() for p in itm.split("::") if p.strip()]
                if len(parts) >= 2:
                    base = f"{prefix}::" + "::".join(parts[:-1]) if prefix else "::".join(parts[:-1])
                    name = parts[-1]
                else:
                    base = prefix
                    name = parts[-1]
            else:
                base = prefix
                name = itm

            mapping.setdefault(base, set()).add(name)

    for it in items:
        handle_item(full_path, it)

    return mapping


def process_simple_import(parts):
    """
    Process a simple import statement without braces.
    
    Args:
        parts: List of parts from splitting the import path by '::'
    
    Returns:
        tuple: (base_path, items)
            - base_path: Base module path
            - items: Set of import items
    """
    # For simple imports like `std::io::Read`
    if len(parts) >= 2:
        # Get the root module for better grouping
        root_module = parts[0]
        
        if len(parts) == 2:
            # For simple two-part paths
            base_path = root_module
            items = {f"{parts[1]}"}
        else:
            # For longer paths, group by top module and preserve submodule structure
            base_path = root_module
            submodule_path = "::".join(parts[1:-1])
            item_name = parts[-1]
            items = {f"{submodule_path}::{item_name}"}
    else:
        # Fallback for unusual cases
        base_path = "::".join(parts[:-1]) if len(parts) > 1 else parts[0]
        items = {parts[-1]}
    
    return base_path, items


def group_imports_by_base_path(use_statements):
    """
    Group imports by their base path.
    
    Args:
        use_statements: List of (cfg_attr, statement, is_pub) tuples
    
    Returns:
        tuple: (grouped_by_base, special_imports)
            - grouped_by_base: Dict mapping (base_path, is_pub) to {cfg_attr: set(import_items)}
            - special_imports: List of special import statements that can't be grouped
    """
    grouped_by_base = {}  # {(base_path, is_pub): {cfg_attr: set(import_items)}}

    # Use the centralized splitter to classify statements
    braced_entries, simple_entries, special_imports = _split_use_statements(use_statements)

    # Handle braced entries (mappings of base_path -> items)
    for cfg_attr, is_pub, mapping in braced_entries:
        for base_path, items in mapping.items():
            key = (base_path, is_pub)
            if key not in grouped_by_base:
                grouped_by_base[key] = {}
            attr_key = cfg_attr or ""
            grouped_by_base[key].setdefault(attr_key, set()).update(items)

    # Handle simple entries (list of path parts)
    for cfg_attr, is_pub, parts in simple_entries:
        base_path, items = process_simple_import(parts)
        key = (base_path, is_pub)
        if key not in grouped_by_base:
            grouped_by_base[key] = {}
        attr_key = cfg_attr or ""
        grouped_by_base[key].setdefault(attr_key, set()).update(items)

    return grouped_by_base, special_imports


def process_nested_module_items(nested_content):
    """
    Process nested module items with brace awareness.
    
    Args:
        nested_content: String containing nested items
    
    Returns:
        tuple: (items_list, has_self)
            - items_list: List of parsed items
            - has_self: Boolean indicating if 'self' is among the items
    """
    # Reuse the brace-aware parser to get ordered nested items and self flag
    return _parse_brace_aware_items(nested_content)


def organize_items_by_module(items):
    """
    Organize import items by their parent module.
    
    Args:
        items: Set of import items
    
    Returns:
        tuple: (module_groups, simple_items)
            - module_groups: Dict mapping module names to their items
            - simple_items: List of simple (non-nested) items
    """
    module_groups = {}
    simple_items = []
    
    for item in items:
        # Handle items with nested braces or module paths
        if "::" in item or "{" in item:
            # Check if this is a submodule path with nested items
            if "{" in item:
                # Extract the module name and its nested items
                module_name = item.split("{")[0].strip().rstrip(":")
                
                # Handle special case with 'self'
                if module_name == 'self':
                    simple_items.append('self')
                    continue
                    
                # Extract nested content handling potential nested braces
                brace_level = 0
                start_idx = item.index("{") + 1
                end_idx = 0
                
                for i, char in enumerate(item[start_idx:], start=start_idx):
                    if char == '{':
                        brace_level += 1
                    elif char == '}':
                        if brace_level == 0:
                            end_idx = i
                            break
                        brace_level -= 1
                
                # If we couldn't properly parse, keep as is
                if end_idx == 0:
                    simple_items.append(item)
                    continue
                
                nested_content = item[start_idx:end_idx].strip()
                
                # Process the nested items with brace awareness
                if module_name not in module_groups:
                    module_groups[module_name] = set()
                
                nested_items, has_nested_self = process_nested_module_items(nested_content)
                
                # Add all non-self items (using set to avoid duplicates)
                module_groups[module_name].update(nested_items)
                
                # If we found 'self', add it separately to ensure it gets sorted to the end
                if has_nested_self:
                    module_groups[module_name].add('self')
            else:
                # This is a module path (like "io::Read" or "file_scan_config::FileScanConfig")
                # Extract the module name and member
                parts = item.split("::")
                if len(parts) >= 2:
                    module_name = parts[0]
                    item_name = "::".join(parts[1:])
                    
                    if module_name not in module_groups:
                        module_groups[module_name] = set()
                    
                    module_groups[module_name].add(item_name)
                else:
                    # Fall back for unusual formats
                    simple_items.append(item)
        else:
            simple_items.append(item)
    
    return module_groups, simple_items


def format_module_groups(module_groups):
    """
    Format module groups into proper import strings.
    
    Args:
        module_groups: Dict mapping module names to their items
    
    Returns:
        list: List of formatted module import strings
    """
    sorted_items = []
    
    # Format nested groups
    for module in sorted(module_groups.keys()):
        # Ensure 'self' comes last in nested groups
        module_items = module_groups[module]
        sorted_module_items = sorted([item for item in module_items if item != 'self'])
        if 'self' in module_items:
            sorted_module_items.append('self')
        
        # Handle single item case without adding unnecessary braces
        if len(sorted_module_items) == 1:
            # For single items, don't add braces no matter what
            sorted_items.append(f"{module}::{sorted_module_items[0]}")
        else:
            nested_content = ", ".join(sorted_module_items)
            sorted_items.append(f"{module}::{{{nested_content}}}")
    
    return sorted_items


def generate_import_statements(grouped_by_base, special_imports):
    """
    Generate consolidated import statements from grouped imports.
    
    Args:
        grouped_by_base: Dict mapping (base_path, is_pub) to {cfg_attr: set(import_items)}
        special_imports: List of special import statements that can't be grouped
    
    Returns:
        list: List of consolidated import statements
    """
    result = []

    # Handle special imports first
    for cfg_attr, stmt, _ in special_imports:
        if cfg_attr:
            result.append(cfg_attr)
        result.append(stmt)

    # Process grouped imports
    for (base_path, is_pub), attr_groups in sorted(grouped_by_base.items()):
        for cfg_attr, items in sorted(attr_groups.items()):
            if cfg_attr:
                result.append(cfg_attr)
            
            prefix = "pub use " if is_pub else "use "
            
            # Organize items by module
            module_groups, simple_items = organize_items_by_module(items)
            
            # Sort simple items (self comes last by convention)
            sorted_simple_items = sorted([item for item in simple_items if item != 'self'])
            if 'self' in simple_items:
                sorted_simple_items.append('self')
            
            # Add sorted module groups
            sorted_items = sorted_simple_items + format_module_groups(module_groups)
            
            # Format the final import statement
            # For readability and consistency with rustfmt standards
            if len(sorted_items) == 1:
                # Single item - no braces needed
                result.append(f"{prefix}{base_path}::{sorted_items[0]};")
            elif any("{" in item for item in sorted_items) or len(sorted_items) > 2:
                result.append(f"{prefix}{base_path}::{{")
                for item in sorted_items:
                    result.append(f"    {item},")
                result.append("};")
            else:
                result.append(f"{prefix}{base_path}::{{{', '.join(sorted_items)}}};")

    return result


def _split_use_statements(use_statements):
    """Split use_statements into braced mappings, simple entries, and special imports.

    Returns:
        braced_entries: list of (cfg_attr, is_pub, mapping) where mapping is base_path->set(items)
        simple_entries: list of (cfg_attr, is_pub, parts) where parts is list of path parts
        special_imports: list of (cfg_attr, statement, is_pub)
    """
    braced_entries = []
    simple_entries = []
    special_imports = []

    for cfg_attr, statement, is_pub in use_statements:
        prefix_len = 8 if is_pub else 4
        import_path = statement[prefix_len:-1].strip()

        if "::" not in import_path or import_path.endswith("::*"):
            special_imports.append((cfg_attr, statement, is_pub))
            continue

        if "{" in import_path:
            mapping = process_import_with_braces(import_path)
            braced_entries.append((cfg_attr, is_pub, mapping))
        else:
            parts = [p for p in import_path.split("::") if p]
            simple_entries.append((cfg_attr, is_pub, parts))

    return braced_entries, simple_entries, special_imports


def collect_root_groups(use_statements):
    """Collect root grouping structure and special imports from parsed use statements."""
    root_groups = {}
    special_imports = []

    for cfg_attr, statement, is_pub in use_statements:
        prefix_len = 8 if is_pub else 4
        import_path = statement[prefix_len:-1].strip()

        if "::" not in import_path or import_path.endswith("::*"):
            special_imports.append((cfg_attr, statement, is_pub))
            continue

        if "{" in import_path:
            mapping = process_import_with_braces(import_path)
            for base_path, items in mapping.items():
                parts = [p for p in base_path.split("::") if p]
                root = parts[0]
                subpath = "::".join(parts[1:]) if len(parts) > 1 else ""

                key = (root, is_pub)
                if key not in root_groups:
                    root_groups[key] = {"order": [], "submap": {}, "attrs": {}}

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

    return root_groups, special_imports


def highest_common_subpath(group):
    """Return the highest common subpath among non-empty subpaths in a group."""
    subpaths = [s for s in group["submap"].keys() if s is not None]
    nonempty = [s for s in subpaths if s]

    if not nonempty:
        return ""

    split_lists = [s.split("::") for s in nonempty]
    common = []
    for parts in zip(*split_lists):
        if all(p == parts[0] for p in parts):
            common.append(parts[0])
        else:
            break

    return "::".join(common) if common else ""


def format_high_group(root, is_pub, group, common_sub):
    """Format a single high-level group into lines.

    Returns a list of lines representing the grouped `use` statement(s).
    """
    lines = []
    prefix = "pub use " if is_pub else "use "

    def _sorted_items(items):
        lower_items = sorted([it for it in items if it and it[0].islower()])
        upper_items = sorted([it for it in items if not (it and it[0].islower())])
        return lower_items + upper_items

    if common_sub:
        # collect everything under common_sub
        inner_map = {}
        for sub, items in group["submap"].items():
            if sub == "":
                remainder = ""
            elif sub.startswith(common_sub):
                remainder = sub[len(common_sub) + 2 :] if len(sub) > len(common_sub) else ""
            else:
                remainder = sub

            inner_map.setdefault(remainder, set()).update(items)

        order = [s for s in group["order"] if s.startswith(common_sub) or s == ""]
        seen = set()
        ordered_remainders = []
        for s in order:
            if s == "":
                r = ""
            elif s.startswith(common_sub):
                r = s[len(common_sub) + 2 :] if len(s) > len(common_sub) else ""
            else:
                r = s
            if r not in seen:
                seen.add(r)
                ordered_remainders.append(r)

        lines.append(f"{prefix}{root}::{common_sub}::{{")
        for rem in ordered_remainders:
            items = inner_map.get(rem, set())
            sorted_items = _sorted_items(items)

            if rem == "":
                if len(sorted_items) == 1:
                    lines.append(f"    {sorted_items[0]},")
                else:
                    lines.append(f"    {{{', '.join(sorted_items)}}},")
            else:
                if len(sorted_items) == 1:
                    lines.append(f"    {rem}::{sorted_items[0]},")
                else:
                    lines.append(f"    {rem}::{{{', '.join(sorted_items)}}},")

        lines.append("};")
    else:
        inner_entries = []
        for sub in group["order"]:
            items = group["submap"][sub]
            sorted_items = _sorted_items(items)

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

        lines.append(f"{prefix}{root}::{{")
        for entry in inner_entries:
            lines.append(f"    {entry},")
        lines.append("};")

    return lines


def collect_low_groups(use_statements):
    """Collect grouping by most-specific base path for low-level grouping.

    Returns:
        grouped_by_base: dict mapping (base_path, is_pub) -> {attr_key: set(items)}
        special_imports: list of special import tuples
    """
    grouped_by_base = {}

    braced_entries, simple_entries, special_imports = _split_use_statements(use_statements)

    for cfg_attr, is_pub, mapping in braced_entries:
        for base_path, items in mapping.items():
            key = (base_path, is_pub)
            if key not in grouped_by_base:
                grouped_by_base[key] = {}
            attr_key = cfg_attr or ""
            grouped_by_base[key].setdefault(attr_key, set()).update(items)

    for cfg_attr, is_pub, parts in simple_entries:
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

    return grouped_by_base, special_imports
