# this file is copied to /Users/kosiew/Library/Application Support/Alfred/Alfred.alfredpreferences/workflows/
# SOURCE_DIR contains the source files for the workflow
import sys
from pathlib import Path

SOURCE_DIR = Path("/Users/kosiew/GitHub/alfred-workflows")

sys.path.insert(0, str(SOURCE_DIR))
import a_weekly_note

a_weekly_note.do()

