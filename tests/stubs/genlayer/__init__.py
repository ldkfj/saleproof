from dataclasses import dataclass as std_dataclass
from typing import Any

u64 = int
Address = str


def allow_storage(cls=None):
    if cls is None:
        return lambda c: c
    return cls


dataclass = std_dataclass


class TreeMap(dict):
    """Dict-backed TreeMap stub for GenLayer testing."""
    pass


class DynArray(list):
    """List-backed DynArray stub for GenLayer testing."""
    pass


class Message:
    def __init__(self):
        self.sender_address: Address = "0x0000000000000000000000000000000000000000"
        self.timestamp: u64 = 1700000000


class Block:
    def __init__(self):
        self.timestamp: u64 = 1700000000


class Public:
    @staticmethod
    def view(fn):
        return fn

    @staticmethod
    def write(fn):
        return fn


class Contract:
    """Base Contract stub that auto-initializes storage fields on instances."""
    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        for attr_name, attr_type in getattr(cls, "__annotations__", {}).items():
            type_str = str(attr_type)
            if "TreeMap" in type_str:
                setattr(instance, attr_name, TreeMap())
            elif "DynArray" in type_str:
                setattr(instance, attr_name, DynArray())
        return instance


class GL:
    def __init__(self):
        self.message = Message()
        self.block = Block()
        self.public = Public()
        self.Contract = Contract


gl = GL()
public = gl.public

__all__ = [
    "gl",
    "public",
    "allow_storage",
    "dataclass",
    "u64",
    "Address",
    "TreeMap",
    "DynArray",
    "Contract",
]
