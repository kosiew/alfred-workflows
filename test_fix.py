#!/usr/bin/env python3

from process_text import streamline_rust_imports

def test_single_item_groups():
    """Test that single-item groups don't use braces."""
    input_text = """use datafusion::common::test_util::batches_to_string;
use datafusion_catalog::MemTable;
use datafusion_common::ScalarValue;"""

    expected_output = """use datafusion::common::test_util::batches_to_string;
use datafusion_catalog::MemTable;
use datafusion_common::ScalarValue;"""

    result = streamline_rust_imports(input_text)
    print("Input:")
    print(input_text)
    print("\nExpected output:")
    print(expected_output)
    print("\nActual output:")
    print(result)
    print("\nTest passed:", result == expected_output)

if __name__ == "__main__":
    test_single_item_groups()
