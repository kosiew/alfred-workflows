from process_text import streamline_rust_imports_unique


def test_remove_exact_duplicates():
    input_text = """
use foo::Bar;
use foo::Bar;

fn main() {}
"""
    # Keep the first occurrence, remove the second, preserve ordering
    expected = """
use foo::Bar;

fn main() {}
"""
    assert streamline_rust_imports_unique(input_text).strip() == expected.strip()


def test_merge_braced_and_simple_duplicates():
    input_text = """
use foo::Bar;
use foo::{Bar};
use foo::{Baz, Qux};
use foo::Qux;
"""
    # We should NOT consolidate imports; only exact duplicates removed.
    out = streamline_rust_imports_unique(input_text).strip().splitlines()
    # Both simple and braced forms should remain (they are not exact duplicates)
    assert any(l.strip() == "use foo::Bar;" for l in out)
    assert any(l.strip() == "use foo::{Bar};" for l in out)
    assert any(l.strip() == "use foo::{Baz, Qux};" for l in out)
    assert any(l.strip() == "use foo::Qux;" for l in out)


def test_cfg_attr_duplicates_kept_separately():
    input_text = """
#[cfg(feature = "x")]
use foo::Bar;
#[cfg(feature = "x")]
use foo::Bar;
#[cfg(feature = "y")]
use foo::Bar;
"""
    out = streamline_rust_imports_unique(input_text).strip().splitlines()
    # The cfg feature x block should appear once, and feature y once
    assert out.count("#[cfg(feature = \"x\")]") == 1
    assert out.count("#[cfg(feature = \"y\")]") == 1