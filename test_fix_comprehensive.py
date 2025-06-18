#!/usr/bin/env python3

from process_text import streamline_rust_imports

def test_multiple_item_groups():
    """Test that multiple-item groups still use braces correctly."""
    input_text = """use std::io::Read;
use std::io::Write;
use std::fs::File;"""

    result = streamline_rust_imports(input_text)
    print("Input:")
    print(input_text)
    print("\nActual output:")
    print(result)
    print("\nShould have braces for multiple items:", "{" in result)

def test_mixed_cases():
    """Test mixed single and multiple item cases."""
    input_text = """use datafusion::common::test_util::batches_to_string;
use datafusion_catalog::MemTable;
use std::io::Read;
use std::io::Write;"""

    result = streamline_rust_imports(input_text)
    print("\nMixed test input:")
    print(input_text)
    print("\nMixed test output:")
    print(result)
    
    # Should have simple imports for single items and braces for multiple
    lines = result.split('\n')
    datafusion_lines = [line for line in lines if 'datafusion' in line]
    std_lines = [line for line in lines if 'std::' in line]
    
    print(f"\nDatafusion lines (should be simple): {datafusion_lines}")
    print(f"Std lines (should have braces): {std_lines}")

if __name__ == "__main__":
    test_multiple_item_groups()
    test_mixed_cases()
