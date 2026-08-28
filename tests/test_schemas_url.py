import pytest
from pydantic import ValidationError

from app.schemas.url import RESERVED_ALIASES, URLCreateRequest


def test_valid_url_no_alias():
    req = URLCreateRequest(original_url="https://example.com/foo")
    assert str(req.original_url).startswith("https://example.com")
    assert req.custom_alias is None


def test_valid_url_with_alias():
    req = URLCreateRequest(
        original_url="https://example.com",
        custom_alias="myAlias1",
    )
    assert req.custom_alias == "myAlias1"


@pytest.mark.parametrize(
    "bad_url",
    [
        "not a url",
        "example.com",
        "ftp://example.com",
        "",
        "http://",
    ],
)
def test_bad_url_rejected(bad_url):
    with pytest.raises(ValidationError):
        URLCreateRequest(original_url=bad_url)


@pytest.mark.parametrize(
    "bad_alias",
    [
        "ab",
        "a" * 17,
        "has-dash",
        "has_underscore",
        "has space",
        "has.dot",
        "unicodé",
        "with/slash",
    ],
)
def test_bad_alias_format_rejected(bad_alias):
    with pytest.raises(ValidationError):
        URLCreateRequest(
            original_url="https://example.com",
            custom_alias=bad_alias,
        )


@pytest.mark.parametrize("reserved", sorted(RESERVED_ALIASES))
def test_reserved_alias_rejected(reserved):
    if not reserved.isalnum() or not (3 <= len(reserved) <= 16):
        pytest.skip("reserved word fails the format check first")
    with pytest.raises(ValidationError):
        URLCreateRequest(
            original_url="https://example.com",
            custom_alias=reserved,
        )


@pytest.mark.parametrize("variant", ["Health", "HEALTH", "hEaLtH"])
def test_reserved_alias_case_insensitive(variant):
    with pytest.raises(ValidationError):
        URLCreateRequest(
            original_url="https://example.com",
            custom_alias=variant,
        )
