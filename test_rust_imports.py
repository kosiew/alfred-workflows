#!/usr/bin/env python3
import sys
sys.path.append('/Users/kosiew/GitHub/alfred-workflows/')
from process_text import streamline_rust_imports

# ===================================================================
# Test Case 1: Basic nested imports
# ===================================================================
test_input1 = '''use std::{
    any::Any,
    fmt::{Display, Formatter},
};
use std::{
    pin::Pin,
    sync::Arc,
    task::{Context, Poll},
};'''

# Test Example 1
result1 = streamline_rust_imports(test_input1)
print("===== EXAMPLE 1: ORIGINAL INPUT =====")
print(test_input1)
print("\n===== EXAMPLE 1: STREAMLINED OUTPUT =====")
print(result1)

# ===================================================================
# Test Case 2: More complex case with multiple modules
# ===================================================================
test_input2 = '''use std::collections::{HashMap, HashSet};
use tokio::sync::{Mutex, RwLock};
use std::io::{self, Read, Write};
use tokio::io::{AsyncRead, AsyncWrite};
use std::collections::BTreeMap;
use std::sync::Arc;
use std::rc::Rc;
use tokio::task;'''

# Test Example 2
result2 = streamline_rust_imports(test_input2)
print("\n\n===== EXAMPLE 2: ORIGINAL INPUT =====")
print(test_input2)
print("\n===== EXAMPLE 2: STREAMLINED OUTPUT =====")
print(result2)

# ===================================================================
# Test Case 3: Complex case with self and deep nesting
# ===================================================================
test_input3 = '''use std::io::{self, Read, BufRead, BufReader, Write};
use serde::{Deserialize, Serialize};
use std::io::Error;
use std::collections::{HashMap, HashSet, BTreeMap, BTreeSet};
use serde::de::{self, Visitor, SeqAccess, MapAccess};
use std::time::{Duration, Instant};
use std::collections::hash_map::{Entry, Iter};
use serde::ser::{SerializeStruct, SerializeSeq};
'''

# Test Example 3
result3 = streamline_rust_imports(test_input3)
print("\n\n===== EXAMPLE 3: ORIGINAL INPUT =====")
print(test_input3)
print("\n===== EXAMPLE 3: STREAMLINED OUTPUT =====")
print(result3)

# ===================================================================
# Test Case 4: Previously problematic input 
# From test_fix_imports.py and test_fix.py
# ===================================================================
test_input4 = '''use std::any::Any;
use std::io::{BufReader, Read, Seek, SeekFrom};
use std::sync::Arc;
use std::task::Poll;'''

# Test Example 4
result4 = streamline_rust_imports(test_input4)
print("\n\n===== EXAMPLE 4: ORIGINAL INPUT =====")
print(test_input4)
print("\n===== EXAMPLE 4: STREAMLINED OUTPUT =====")
print(result4)

# ===================================================================
# Test Case 5: Imports from same module but different submodules
# From test_common_module.py and test_data_fusion.py
# ===================================================================
test_input5 = '''use datafusion_datasource::file::{FileSource};
use datafusion_datasource::file_scan_config::{FileScanConfig};'''

# Test Example 5
result5 = streamline_rust_imports(test_input5)
print("\n\n===== EXAMPLE 5: ORIGINAL INPUT =====")
print(test_input5)
print("\n===== EXAMPLE 5: STREAMLINED OUTPUT =====")
print(result5)
