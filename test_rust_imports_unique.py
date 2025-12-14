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
    # Semantically-equivalent variants should dedupe; the first occurrence
    # (simple form) is kept and the braced form removed.
    assert any(l.strip() == "use foo::Bar;" for l in out)
    assert not any(l.strip() == "use foo::{Bar};" for l in out)
    assert any(l.strip() == "use foo::{Baz, Qux};" for l in out)
    # The later simple form is semantically duplicate of the earlier braced form
    assert not any(l.strip() == "use foo::Qux;" for l in out)


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


def test_nested_brace_deduplication():
    input_text = """
use foo::{bar::{A, B}, C};
use foo::bar::A;
use foo::C;

fn main() {}
"""
    out = streamline_rust_imports_unique(input_text).strip().splitlines()
    # First complex braced import should remain, following semantically-equal
    # imports should be removed
    assert any(l.strip() == "use foo::{bar::{A, B}, C};" for l in out)
    assert not any(l.strip() == "use foo::bar::A;" for l in out)
    assert not any(l.strip() == "use foo::C;" for l in out)


def test_spacing_variations_deduplication():
    input_text = """
use foo::Bar;
use  foo :: { Bar } ;

fn main() {}
"""
    out = streamline_rust_imports_unique(input_text).strip().splitlines()
    # Spacing/formatting variations should be treated as duplicates
    assert sum(1 for l in out if l.strip() == "use foo::Bar;") == 1


def test_cfg_whitespace_normalization_deduplication():
    input_text = """
#[cfg(feature = "x")]
use foo::Bar;
#[cfg( feature= "x" )]
use foo::Bar;

fn main() {}
"""
    out = streamline_rust_imports_unique(input_text).strip().splitlines()
    # cfg variants with different whitespace should dedupe
    assert sum(1 for l in out if l.strip().startswith("#[cfg")) == 1
    assert any(l.strip() == "use foo::Bar;" for l in out)