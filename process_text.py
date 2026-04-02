# this file is copied to /Users/kosiew/Library/Application Support/Alfred/Alfred.alfredpreferences/workflows/
# SOURCE_DIR contains the source files for the workflow
import sys
from pathlib import Path

SOURCE_DIR = Path("/Users/kosiew/GitHub/alfred-workflows")

sys.path.insert(0, str(SOURCE_DIR))
import a_process_text

# Expose a_process_text symbols for easier import-based testing.
from a_process_text import *

if __name__ == "__main__":
    a_process_text.do()

