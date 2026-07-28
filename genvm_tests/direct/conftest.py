import os
from pathlib import Path
import sys
import pytest
from gltest.direct.vm import VMContext
from gltest.direct import wasi_mock, loader

# Ensure root directory is on sys.path for test discovery (without adding tests/stubs)
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Ensure os.fdopen is patched for Direct Mode WASI mocks
os.fdopen = wasi_mock.patched_fdopen

# Patch _load_module to reset __known_contract__ RIGHT BEFORE executing the contract module
_orig_load_module = loader._load_module


def _patched_load_module(contract_path):
    if "genlayer.gl.genvm_contracts" in sys.modules:
        sys.modules["genlayer.gl.genvm_contracts"].__known_contract__ = None
    return _orig_load_module(contract_path)


loader._load_module = _patched_load_module

# Patch VMContext.warp to update datetime in gl.message_raw
_orig_warp = VMContext.warp


def _patched_warp(self, timestamp: str) -> None:
    _orig_warp(self, timestamp)
    if "genlayer.gl" in sys.modules:
        gl = sys.modules["genlayer.gl"]
        if hasattr(gl, "message_raw") and isinstance(gl.message_raw, dict):
            gl.message_raw["datetime"] = timestamp


VMContext.warp = _patched_warp


@pytest.fixture(autouse=True)
def reset_direct_contract_registry():
    if "genlayer.gl.genvm_contracts" in sys.modules:
        sys.modules["genlayer.gl.genvm_contracts"].__known_contract__ = None
    yield
    if "genlayer.gl.genvm_contracts" in sys.modules:
        sys.modules["genlayer.gl.genvm_contracts"].__known_contract__ = None
