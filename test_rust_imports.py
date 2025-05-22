#!/usr/bin/env python3
import sys
from process_text import streamline_rust_imports

test_input = '''use std::{
    any::Any,
    fmt::{Display, Formatter},
};
use std::{
    pin::Pin,
    sync::Arc,
    task::{Context, Poll},
};'''

result = streamline_rust_imports(test_input)
print("Original input:")
print(test_input)
print("\nStandardized output:")
print(result)
