from process_text import streamline_rust_imports

test_input = """use datafusion_datasource::file::{FileSource};
use datafusion_datasource::file_scan_config::{FileScanConfig};
"""

result = streamline_rust_imports(test_input)
print("===== ORIGINAL INPUT =====")
print(test_input)
print("\n===== STREAMLINED OUTPUT =====")
print(result)
