#!/usr/bin/env python3

# Test the updated streamline_python_imports function
import sys
import os
sys.path.append('/Users/kosiew/GitHub/alfred-workflows')

from process_text import streamline_python_imports

# Test case with multiple imports that should be formatted as multi-line
test_input = """from . import functions, object_store, substrait, unparser
from collections import defaultdict, Counter
from typing import List
import os
import sys"""

print("Input:")
print(test_input)
print("\nOutput:")
result = streamline_python_imports(test_input)
print(result)
