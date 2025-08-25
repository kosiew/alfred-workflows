from process_text import (
    streamline_rust_imports,
    streamline_rust_imports_high,
    streamline_rust_imports_low,
)

examples = [
    # Example 1: multi-level imports where high groups to root module but low keeps specific base
    (
        "Example 1 - multi-level paths",
        """
use arrow::array::ArrayRef;
use arrow::datatypes::DataType;
use arrow::array::Array;
        """,
    ),

    # Example 2: braced imports mixing submodules
    (
        "Example 2 - braced nested",
        """
use arrow::array::{ArrayRef, UInt32Array};
use arrow::array::builder::ArrayBuilder;
use arrow::datatypes::{DataType, Field};
        """,
    ),

    # Example 3: deeper common subpath
    (
        "Example 3 - common subpath",
        """
use foo::bar::baz::ThingA;
use foo::bar::baz::ThingB;
use foo::bar::other::ThingC;
        """,
    ),

    # Example 4: single-item imports from many long paths
    (
        "Example 4 - long single items",
        """
use alpha::beta::gamma::X;
use alpha::beta::delta::Y;
use alpha::zeta::W;
        """,
    ),
]

for title, src in examples:
    print("=" * 40)
    print(title)
    print("- source:\n")
    print(src)
    print("- streamline_rust_imports (default):\n")
    print(streamline_rust_imports(src))
    print("\n- streamline_rust_imports_low:\n")
    print(streamline_rust_imports_low(src))
    print("\n- streamline_rust_imports_high:\n")
    print(streamline_rust_imports_high(src))


print("Done")
