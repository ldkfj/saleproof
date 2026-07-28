import pytest
import datetime
from pathlib import Path
import sys
import os

# Ensure root, contracts, and stubs are importable
root_dir = str(Path(__file__).parent.parent.parent)
stubs_dir = str(Path(__file__).parent.parent.parent / "tests" / "stubs")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if stubs_dir not in sys.path:
    sys.path.insert(0, stubs_dir)


class DirectVMSimulator:
    def __init__(self):
        self.check_pickling = True
        self.strict_mocks = True
        self.timestamp = 1785196800  # 2026-07-28T00:00:00Z
        self.datetime = datetime.datetime(2026, 7, 28, 0, 0, 0, tzinfo=datetime.timezone.utc)

    def warp_time(self, new_timestamp: int):
        self.timestamp = new_timestamp
        self.datetime = datetime.datetime.fromtimestamp(new_timestamp, tz=datetime.timezone.utc)


@pytest.fixture
def direct_vm():
    vm = DirectVMSimulator()
    return vm
