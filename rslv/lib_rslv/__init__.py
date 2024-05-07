import importlib
import typing
import urllib.parse


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


def unsplit_identifier_string(template_str:str, pid_parts:dict) -> str:
    """Unsplit a dict of identifier components.

    template_str is a python fstring compatible string that will be filled with
    values from pid_parts. If as_url is set, then pid_parts are url encoded first.
    """
    encoded_pid_parts = pid_parts.copy()
    encoded_pid_parts["pid_enc"] = urllib.parse.quote(pid_parts["pid"])
    encoded_pid_parts["scheme_enc"] = urllib.parse.quote(pid_parts["scheme"])
    encoded_pid_parts["content_enc"] = urllib.parse.quote(pid_parts["content"])
    encoded_pid_parts["prefix_enc"] = urllib.parse.quote(pid_parts["prefix"])
    encoded_pid_parts["value_enc"] = urllib.parse.quote(pid_parts["value"])
    return template_str.format(**encoded_pid_parts)
