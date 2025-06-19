#!/usr/bin/env python3
import sys
sys.path.append('/Users/kosiew/GitHub/alfred-workflows/')
from process_text import streamline_rust_imports

# Test the specific arrow imports issue
test_input = '''use arrow::array::*;
use arrow::datatypes::*;'''

print("===== ORIGINAL INPUT =====")
print(test_input)

result = streamline_rust_imports(test_input)
print("\n===== STREAMLINED OUTPUT =====")
print(result)

print("\n===== EXPECTED OUTPUT =====")
print("use arrow::{array::*, datatypes::*};")
