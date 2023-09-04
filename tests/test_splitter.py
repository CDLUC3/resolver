import pytest
import rslv.lib_rslv

split_tests = (
    ("", {"pid": "", "scheme": "", "content": None, "prefix": None, "value": None}),
    (
        "simple:test",
        {
            "pid": "simple:test",
            "scheme": "simple",
            "content": "test",
            "prefix": "test",
            "value": None,
        },
    ),
    (
        " test : basic ",
        {
            "pid": "test : basic",
            "scheme": "test",
            "content": "basic",
            "prefix": "basic",
            "value": None,
        },
    ),
    (
        "foo:/",
        {
            "pid": "foo:/",
            "scheme": "foo",
            "content": "",
            "prefix": "",
            "value": None,
        },
    ),
    (
        " test : basic // foo ",
        {
            "pid": "test : basic // foo",
            "scheme": "test",
            "content": "basic // foo",
            "prefix": "basic",
            "value": "foo",
        },
    ),
    (
        "ark:/12345/foo?baz",
        {
            "pid": "ark:/12345/foo?baz",
            "scheme": "ark",
            "content": "12345/foo?baz",
            "prefix": "12345",
            "value": "foo?baz",
        },
    ),
    (
        "ark:12345//foo?baz",
        {
            "pid": "ark:12345//foo?baz",
            "scheme": "ark",
            "content": "12345//foo?baz",
            "prefix": "12345",
            "value": "foo?baz",
        },
    ),
    (
        "doi:10.12345/foo?baz",
        {
            "pid": "doi:10.12345/foo?baz",
            "scheme": "doi",
            "content": "10.12345/foo?baz",
            "prefix": "10.12345",
            "value": "foo?baz",
        },
    ),
    (
        "IGSN:AU1243",
        {
            "pid": "IGSN:AU1243",
            "scheme": "igsn",
            "content": "AU1243",
            "prefix": "AU1243",
            "value": None,
        },
    ),
    (
        "gmd:68513255-fc44-4041-bc4b-4fd2fae7541d",
        {
            "pid": "gmd:68513255-fc44-4041-bc4b-4fd2fae7541d",
            "scheme": "gmd",
            "content": "68513255-fc44-4041-bc4b-4fd2fae7541d",
            "prefix": "68513255-fc44-4041-bc4b-4fd2fae7541d",
            "value": None,
        },
    ),
    (
        "inchi:InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
        {
            "pid": "inchi:InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
            "scheme": "inchi",
            "content": "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
            "prefix": "InChI=1S",
            "value": "C2H6O/c1-2-3/h3H,2H2,1H3",
        },
    ),
    (
        "orcid:0000-0002-5355-2576",
        {
            "pid": "orcid:0000-0002-5355-2576",
            "scheme": "orcid",
            "content": "0000-0002-5355-2576",
            "prefix": "0000-0002-5355-2576",
            "value": None,
        },
    ),
    (
        "z017/biomodels.db:BIOMD0000000048",
        {
            "pid": "z017/biomodels.db:BIOMD0000000048",
            "scheme": "z017/biomodels.db",
            "content": "BIOMD0000000048",
            "prefix": "BIOMD0000000048",
            "value": None,
        },
    ),
)

@pytest.mark.parametrize("test,expected", split_tests)
def test_split(test, expected):
    result = rslv.lib_rslv.split_identifier_string(test)
    for k, v in expected.items():
        assert result[k] == expected[k]
