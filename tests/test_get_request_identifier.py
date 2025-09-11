import pytest


from rslv.routers.resolver import CleanedIdentifierRequest


test_cases = (
    (
        {
            "url": "http://example.com/ark:/12345/foo",
            "identifier": "ark:/12345/foo"
        },
        {
            "original": "ark:/12345/foo",
            "cleaned": "ark:/12345/foo",
            "is_introspection": False,
            "has_service_url": False,
        }
    ),
    (
        {
            "url": "http://example.com/ark:/22345/foo?info",
            "identifier": "ark:/22345/foo?info"
        },
        {
            "original": "ark:/22345/foo?info",
            "cleaned": "ark:/22345/foo",
            "is_introspection": True,
            "has_service_url": False,
        }
    ),
    (
        {
            "url": "http://example.com/ark%3A/12345/foo",
            "identifier": "ark%3A/12345/foo"
        },
        {
            "original": "ark:/12345/foo",
            "cleaned": "ark:/12345/foo",
            "is_introspection": False,
            "has_service_url": False,
        }
    ),
    (
        {
            "url": "http://example.com/ark%3A/22345/foo?info",
            "identifier": "ark:/22345/foo?info"
        },
        {
            "original": "ark:/22345/foo?info",
            "cleaned": "ark:/22345/foo",
            "is_introspection": True,
            "has_service_url": False,
        }
    ),
    (
        {
            "url": "http://example.com/http://example.com/ark:/32345/foo",
            "identifier": "http://example.com/ark:/32345/foo"
        },
        {
            "original": "ark:/32345/foo",
            "cleaned": "ark:/32345/foo",
            "is_introspection": False,
            "has_service_url": True,
        }
    ),
    (
        {
            "url": "http://example.com/http%3A%2F%2Fexample.com%2Fark%3A%2F42345%2Ffoo",
            "identifier": "http://example.com/ark:/42345/foo"
        },
        {
            "original": "ark:/42345/foo",
            "cleaned": "ark:/42345/foo",
            "is_introspection": False,
            "has_service_url": True,
        }
    ),
    (
        {
            "url": "http://example.com/http%3A%2F%2Fexample.com%2Fark%3A%2F52345%2Ffoo??",
            "identifier": "http://example.com/ark:/52345/foo??"
        },
        {
            "original": "ark:/52345/foo??",
            "cleaned": "ark:/52345/foo",
            "is_introspection": True,
            "has_service_url": True,
        }
    ),
    (
        {
            "url": "http://example.com/purl:dc/terms/creator",
            "identifier": "purl:dc/terms/creator"
        },
        {
            "original": "purl:dc/terms/creator",
            "cleaned": "purl:dc/terms/creator",
            "is_introspection": False,
            "has_service_url": False,
        }
    ),
    (
        {
            "url": "http://example.com/purl:dc/terms/creator?",
            "identifier": "purl:dc/terms/creator"
        },
        {
            "original": "purl:dc/terms/creator?",
            "cleaned": "purl:dc/terms/creator",
            "is_introspection": True,
            "has_service_url": False,
        }
    ),
)

@pytest.mark.parametrize("test,expected", test_cases)
def test_get_request_identifier(test, expected):
    res = CleanedIdentifierRequest.from_request_url(test["url"], test["identifier"], service_pattern=r"^https?://example.com/")
    assert res.original == expected["original"]
    assert res.cleaned == expected["cleaned"]
    assert res.is_introspection == expected["is_introspection"]
    assert res.has_service_url == expected["has_service_url"]
