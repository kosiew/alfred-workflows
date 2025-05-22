import sys
sys.path.append('/Users/kosiew/GitHub/alfred-workflows/')
from process_text import streamline_rust_imports

# Example 1: Basic nested imports
test_input1 = '''use std::{
    any::Any,
    fmt::{Display, Formatter},
};
use std::{
    pin::Pin,
    sync::Arc,
    task::{Context, Poll},
};'''

# Example 2: More complex case with multiple modules
test_input2 = '''use std::collections::{HashMap, HashSet};
use tokio::sync::{Mutex, RwLock};
use std::io::{self, Read, Write};
use tokio::io::{AsyncRead, AsyncWrite};
use std::collections::BTreeMap;
use std::sync::Arc;
use std::rc::Rc;
use tokio::task;'''

# Test Example 1
result1 = streamline_rust_imports(test_input1)
print("===== EXAMPLE 1: ORIGINAL INPUT =====")
print(test_input1)
print("\n===== EXAMPLE 1: STREAMLINED OUTPUT =====")
print(result1)

# Test Example 2
result2 = streamline_rust_imports(test_input2)
print("\n\n===== EXAMPLE 2: ORIGINAL INPUT =====")
print(test_input2)
print("\n===== EXAMPLE 2: STREAMLINED OUTPUT =====")
print(result2)

# Example 3: Complex case with self and deep nesting
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
