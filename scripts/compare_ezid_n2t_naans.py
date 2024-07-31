"""
Determine NAANs with known shoulders that are EZID managed and so
must have target adjusted to override the configuration currently
available in the NAAN registry.

The file "ezid_naans.json" is written to the current folder when
this script is run. That file is used as input when loading NAAN
configuration using the `rslv naans` command (implemented in manage.py).
"""

raise NotImplementedError("This script is deprecated")

import json
import os
import re

import rslv.lib_rslv.n2tutils

re_ark = re.compile(
    r"\b(?P<PID>ark:/?(?P<prefix>[0-9]{5,10})\/(?P<value>\S+)?)",
    re.IGNORECASE | re.MULTILINE,
)


def get_ark_pids_from_shoulder_list(list_fn):
    text = open(list_fn, "r").read()
    result = re_ark.finditer(text)
    pids = []
    for row in result:
        pid = {
            "scheme": "ark",
            "prefix": row.group("prefix"),
            "value": "" if row.group("value") is None else row.group("value"),
        }
        pids.append(pid)
    return pids


def get_ark_shoulders_from_full_prefixes(prefixes_fn):
    text = open(prefixes_fn, "r").read()
    records = rslv.lib_rslv.n2tutils.n2t_prefixes_from_yaml(text)
    shoulders = []
    for k, record in records.items():
        if record.get("type") == "shoulder":
            parts = rslv.lib_rslv.split_identifier_string(k)
            shoulders.append(parts)
    return shoulders


def main():
    ezid_shoulder_txt = "ezid-shoulder-list.txt"
    n2t_prefixes_txt = "n2t_full_prefixes.yaml"
    ezid_naans_json = "ezid_naans.json"
    if not os.path.exists(ezid_shoulder_txt):
        print(
            f"{ezid_shoulder_txt} not found in the current folder. Generate from ezid using manage.py shoulder-list > {ezid_shoulder_txt}"
        )
        return
    if not os.path.exists(n2t_prefixes_txt):
        print(
            f"{n2t_prefixes_txt} not found in the current folder. Get it from N2T from 'https://n2t.net/e/n2t_full_prefixes.yaml'"
        )
        return
    print(f"Loading from {ezid_shoulder_txt}...")
    ezid_shoulders = get_ark_pids_from_shoulder_list(ezid_shoulder_txt)
    print(f"Loading from {n2t_prefixes_txt}...")
    n2t_shoulders = get_ark_shoulders_from_full_prefixes(n2t_prefixes_txt)
    ezid_naans = set()
    for pid in ezid_shoulders:
        naan = pid.get("prefix")
        if naan is not None:
            ezid_naans.add(naan)
    n2t_naans = set()
    for pid in n2t_shoulders:
        if pid.get("scheme") == "ark":
            naan = pid.get("prefix")
            if naan is not None:
                n2t_naans.add(naan)

    print("EZID:")
    print(ezid_naans)
    print("N2T:")
    print(ezid_naans)
    print("Only N2T:")
    print(n2t_naans.difference(ezid_naans))
    with open(ezid_naans_json, "w") as dest:
        json.dump(list(ezid_naans), dest)
    print(f"EZID NAANs written to {ezid_naans_json}")


if __name__ == "__main__":
    main()
