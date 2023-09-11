"""
Attempting to determine naans with known shoulders that are not EZID and behave
differently to the available public configuration.
"""

import json
import logging
import re
import click

import rslv.lib_rslv.n2tutils

re_ark = re.compile(
    r"\b(?P<PID>ark:/?(?P<prefix>[0-9]{5,10})\/(?P<value>\S+)?)",
    re.IGNORECASE | re.MULTILINE
)


def get_ark_pids_from_shoulder_list(list_fn):
    text = open(list_fn, "r").read()
    result = re_ark.finditer(text)
    pids = []
    for row in result:
        pid = {
            "scheme": "ark",
            "prefix": row.group("prefix"),
            "value": "" if row.group("value") is None else row.group("value")
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
    ezid_shoulders = get_ark_pids_from_shoulder_list("ezid-shoulder-list.txt")
    n2t_shoulders = get_ark_shoulders_from_full_prefixes("n2t_full_prefixes.yaml")
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
    with open("ezid_naans.json", "w") as dest:
        json.dump(list(ezid_naans), dest)





if __name__ == "__main__":
    main()