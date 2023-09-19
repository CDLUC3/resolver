import importlib
import typing
import pydantic


def load_parser(class_name):
    pkg, cls = class_name.rsplit(".", 1)
    _module = importlib.import_module(pkg)
    return getattr(_module, cls)


def null_value_cleaner(o, v):
    return v

def ark_value_cleaner(o, v):
    res = v.replace("-", "")
    return res


class ParsedPID(pydantic.BaseModel):
    pid: str
    scheme: str = ""
    content: typing.Optional[str] = None
    prefix: typing.Optional[str] = None
    value: typing.Optional[str] = None
    clean_value: typing.Optional[str] = None
    _value_cleaner:typing.Callable[['ParsedPid',str], str] = null_value_cleaner

    @property
    def uniq(self) -> str:
        res = f"{self.scheme}"
        if self.prefix is not None:
            res = f"{res}:{self.scheme}"
        if self.value is not None:
            res = f"{res}/{self.value}"
        return res

    def split_scheme(self):
        _parts = self.pid.split(":", 1)
        self.scheme = _parts[0].strip().lower()
        try:
            self.content = _parts[1].lstrip(" /:")
            self.content = self.content.strip()
        except IndexError:
            self.content = None

    def split_content(self):
        self.prefix = None
        self.value = None
        if self.content is None:
            return
        _parts = self.content.split("/", 1)
        self.prefix = _parts[0].strip()
        try:
            self.value = _parts[1].lstrip(" /")
            self.value = self.value.strip()
        except IndexError:
            pass

    def process_value(self):
        if isinstance(self._value_cleaner, typing.Callable):
            self.clean_value = self._value_cleaner(self.value)

    def split(self):
        self.pid = self.pid.strip()
        self.split_scheme()
        if self.content is not None:
            self.split_content()
            if self.value is not None:
                self.process_value()



def split_identifier_string(pid_str: str) -> typing.Dict[str, typing.Any]:
    pid_str = pid_str.strip()
    parsed = {
        "pid": pid_str,
        "scheme": "",
        "content": None,
        "prefix": None,
        "value": None,
    }
    _parts = pid_str.split(":",1)
    parsed["scheme"] = _parts[0].strip().lower()
    try:
        parsed["content"] = _parts[1].lstrip(" /:")
        parsed["content"] = parsed["content"].strip()
    except IndexError:
        return parsed
    _parts = parsed["content"].split("/", 1)
    parsed["prefix"] = _parts[0].strip()
    try:
        parsed["value"] = _parts[1].lstrip(" /")
        parsed["value"] = parsed["value"].strip()
    except IndexError:
        pass
    return parsed
