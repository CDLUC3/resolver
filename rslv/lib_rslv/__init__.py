import importlib
import re
import typing
import urllib.parse


# regexp for matching a general identifier pattern of scheme:content
RE_IDENTIFIER = re.compile(
    r"\b(?P<PID>(?P<scheme>[A-Za-z0-9/;.\-]+):/?(?P<content>\S+))\b",
    re.IGNORECASE | re.MULTILINE
)


def load_parser(class_name):
    pkg, cls = class_name.rsplit(".", 1)
    _module = importlib.import_module(pkg)
    return getattr(_module, cls)


def split_identifier_string(pid_str: str) -> typing.Dict[str, typing.Any]:
    """
    Split an identifier.
    ark:/12345/bar =>
        pid = ark:/12345/bar
        scheme = ark
        content = 12345/bar
        prefix = 12345
        value = bar
    """
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


def identifiers_in_text(text: str) -> typing.Generator[dict, None, int]:
    count = 0
    for match in RE_IDENTIFIER.finditer(text):
        pid = {
            "pid": match.group("PID"),
            "scheme": match.group('scheme'),
            "content": match.group('content'),
        }
        count += 1
        yield pid
    return count

def remove_hyphens(text: typing.Optional[str]) -> typing.Optional[str]:
    # removes hyphens, but not from query part...
    if text is None:
        return text
    ab = text.split("?", 1)
    a = ab[0].replace("-", "")
    if len(ab) < 2:
        return a
    return f"{a}?{ab[1]}"

