from process_text import streamline_rust_imports


def test_scalarvalue_and_tree_node_grouping():
    input_text = '''use datafusion_common::tree_node::TreeNodeRecursion;
use datafusion_common::ScalarValue;
'''

    expected = '''use datafusion_common::{
    tree_node::TreeNodeRecursion,
    ScalarValue,
};'''

    assert streamline_rust_imports(input_text).strip() == expected.strip()
