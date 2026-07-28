u64 = int
u256 = int


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

    def get_or_insert_default(self, key):
        if key not in self:
            self[key] = DynArray()
        return self[key]


class DynArray(list):
    """List-backed DynArray stub for GenLayer testing."""
    pass


class Message:
    def __init__(self):
        self.sender_address: Address = Address("0x0000000000000000000000000000000000000000")
        self.value: u256 = 0


class Write:
    def __call__(self, fn):
        return fn

    def payable(self, fn):
        return fn


class Public:
    def __init__(self):
        self.write = Write()

    @staticmethod
    def view(fn):
        return fn


class Evm:
    @staticmethod
    def contract_interface(cls):
        return cls


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


class UserError(Exception):
    """GenVM user exception type."""

    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message


class Return:
    """GenVM Return type wrapper passed to validator closures."""

    def __init__(self, value):
        self.value = value


class VM:
    def __init__(self, gl_ref):
        self._gl = gl_ref
        self.UserError = UserError
        self.Return = Return

    def run_nondet_unsafe(self, leader_fn, validator_fn):
        leader_res = leader_fn()
        wrapped = Return(leader_res)
        agreed = validator_fn(wrapped)
        if not agreed:
            raise UserError("MAJORITY_DISAGREE")
        return leader_res


class StorageSlot:
    def __init__(self, initial=None, is_code_slot=False):
        self._value = initial if initial is not None else DynArray()
        self._is_code_slot = is_code_slot

    def get(self):
        return self

    def append(self, val):
        self._value.append(val)

    def truncate(self):
        if self._is_code_slot:
            sender = gl.message.sender_address
            upgraders = Root.get().upgraders._value
            if sender not in upgraders:
                raise UserError("ERR_NOT_UPGRADER")
        self._value.clear()

    def extend(self, new_val):
        if self._is_code_slot:
            sender = gl.message.sender_address
            upgraders = Root.get().upgraders._value
            if sender not in upgraders:
                raise UserError("ERR_NOT_UPGRADER")
        if isinstance(new_val, (bytes, bytearray, list)):
            self._value.extend(new_val)
        else:
            self._value.append(new_val)

    def __eq__(self, other):
        return self._value == other

    def __iter__(self):
        return iter(self._value)


class Root:
    _instance = None

    def __init__(self):
        self.upgraders = StorageSlot(DynArray())
        self.code = StorageSlot(bytearray(), is_code_slot=True)

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = cls()


class Storage:
    def __init__(self):
        self.Root = Root


class GL:
    def __init__(self):
        self.message = Message()
        self.public = Public()
        self.Contract = Contract
        self.evm = Evm()
        self.nondet = Nondet(self)
        self.eq_principle = EqPrinciple(self)
        self.vm = VM(self)
        self.storage = Storage()

        # Settable fakes & recorded call history for tests
        self._fake_contract = None
        self._fake_page: str = ""
        self._fake_llm_output: str = ""
        self._last_url: str = ""
        self._last_mode: str = ""
        self._last_prompt: str = ""
        self._last_criteria: str = ""

    def get_contract_at(self, addr):
        return self._fake_contract


gl = GL()
public = gl.public

__all__ = [
    "gl",
    "public",
    "allow_storage",
    "u64",
    "u256",
    "Address",
    "TreeMap",
    "DynArray",
    "Contract",
]
