import importlib
import typing


def load_parser(class_name):
    pkg, cls = class_name.rsplit(".", 1)
    _module = importlib.import_module(pkg)
    return getattr(_module, cls)


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
