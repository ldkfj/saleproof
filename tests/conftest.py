import sys
from pathlib import Path

# Inject tests/stubs into sys.path BEFORE any test imports the contract
stubs_path = str(Path(__file__).parent / "stubs")
if stubs_path not in sys.path:
    sys.path.insert(0, stubs_path)

# Also ensure root and contracts/ are in sys.path for direct contract imports
root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)
