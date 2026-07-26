u64 = int


class Address:
    """Mirrors the real Address: constructed from hex str or 20 bytes; equality/hash on normalized hex."""

    def __init__(self, val):
        if isinstance(val, Address):
            self._hex = val._hex
            return
        if isinstance(val, (bytes, bytearray)):
            b = bytes(val)
            if len(b) != 20:
                raise ValueError("Address bytes must be length 20")
            self._hex = "0x" + b.hex()
            return
        if isinstance(val, str):
            s = val.lower()
            if s.startswith("0x"):
                s = s[2:]
            if len(s) != 40:
                raise ValueError("Address hex must be 40 chars")
            int(s, 16)
            self._hex = "0x" + s
            return
        raise TypeError("Address accepts str or 20 bytes")

    def __str__(self):
        return self._hex

    def __repr__(self):
        return f"Address({self._hex})"

    def __eq__(self, other):
        try:
            o = other if isinstance(other, Address) else Address(other)
        except Exception:
            return NotImplemented
        return self._hex == o._hex

    def __hash__(self):
        return hash(self._hex)


def allow_storage(cls=None):
    if cls is None:
        return lambda c: c
    return cls


class TreeMap(dict):
    """Dict-backed TreeMap stub for GenLayer testing."""
    pass


class DynArray(list):
    """List-backed DynArray stub for GenLayer testing."""
    pass


class Message:
    def __init__(self):
        self.sender_address: Address = "0x0000000000000000000000000000000000000000"


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


class Web:
    def __init__(self, gl_ref):
        self._gl = gl_ref

    def render(self, url: str, mode: str = "text") -> str:
        self._gl._last_url = url
        self._gl._last_mode = mode
        return self._gl._fake_page


class Nondet:
    def __init__(self, gl_ref):
        self._gl = gl_ref
        self.web = Web(gl_ref)

    def exec_prompt(self, prompt: str) -> str:
        self._gl._last_prompt = prompt
        return self._gl._fake_llm_output


class EqPrinciple:
    def __init__(self, gl_ref):
        self._gl = gl_ref

    def prompt_comparative(self, fn, criteria: str):
        self._gl._last_criteria = criteria
        return fn()


class GL:
    def __init__(self):
        self.message = Message()
        self.public = Public()
        self.Contract = Contract
        self.nondet = Nondet(self)
        self.eq_principle = EqPrinciple(self)

        # Settable fakes & recorded call history for tests
        self._fake_page: str = ""
        self._fake_llm_output: str = ""
        self._last_url: str = ""
        self._last_mode: str = ""
        self._last_prompt: str = ""
        self._last_criteria: str = ""


gl = GL()
public = gl.public

__all__ = [
    "gl",
    "public",
    "allow_storage",
    "u64",
    "Address",
    "TreeMap",
    "DynArray",
    "Contract",
]
