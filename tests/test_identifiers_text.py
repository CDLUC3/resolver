import pytest

import rslv.lib_rslv.n2tutils

test_cases = (
    ("", ()),
    ("aslkdnasdf foo:bar/baz salkfaf", ({"pid": "foo:bar/baz", "scheme": "foo"},)),
    ("ark:12345/foo/bar", ({"pid": "ark:12345/foo/bar", "scheme": "ark"},)),
    ("ark:/12345/foo/bar", ({"pid": "ark:/12345/foo/bar", "scheme": "ark"},)),
    (
        """Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua (doi:10.1234/aliqua). In metus
vulputate eu scelerisque felis imperdiet proin fermentum. Urna porttitor rhoncus
dolor purus non enim: z017/biomodels.db:BIOMD0000000048. Massa sed elementum
tempus signaling-gateway:A001094, gmd:68513255-fc44-4041-bc4b-4fd2fae7541d egestas
sed sed risus pretium.""",
        (
            {"pid": "doi:10.1234/aliqua", "scheme": "doi"},
            {"pid": "z017/biomodels.db:BIOMD0000000048", "scheme": "z017/biomodels.db"},
            {"pid": "signaling-gateway:A001094", "scheme": "signaling-gateway"},
            {"pid": "gmd:68513255-fc44-4041-bc4b-4fd2fae7541d", "scheme": "gmd"},
        ),
    ),
)


def cmp_pid(a, b):
    for k in (
        "pid",
        "scheme",
    ):
        if a.get(k) != b.get(k):
            return False
    return True


def pid_in_list(alist, b):
    for a in alist:
        if cmp_pid(a, b):
            return True
    return False


def test_cmp_pid():
    assert cmp_pid({"pid": "a"}, {"pid": "a"})


def test_pid_in_list():
    alist = (
        {"pid": "a"},
        {"pid": "b"},
    )
    b = {"pid": "a"}
    assert pid_in_list(alist, b)


@pytest.mark.parametrize("input,expected", test_cases)
def test_match_in_text(input, expected):
    matches = []
    for pid in rslv.lib_rslv.n2tutils.identifiers_in_text(input):
        matches.append(pid)
        assert pid_in_list(expected, pid)

    assert len(matches) == len(expected)
