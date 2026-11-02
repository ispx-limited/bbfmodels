from datetime import UTC, datetime
from decimal import Decimal

import pytest

from bbfmodels import codec
from bbfmodels.ir import (
    BaseType,
    Enumeration,
    EnumerationRef,
    Facets,
    ListFacets,
    Pattern,
    Range,
    Size,
    Syntax,
)


def syntax(base: BaseType, **kw: object) -> Syntax:
    return Syntax(base_type=base, **kw)  # type: ignore[arg-type]


def test_scalars_decode_and_encode() -> None:
    cases: list[tuple[BaseType, str, codec.Scalar, str]] = [
        (BaseType.STRING, "a,b", "a,b", "a,b"),
        (BaseType.BOOLEAN, "1", True, "true"),
        (BaseType.BOOLEAN, "false", False, "false"),
        (BaseType.INT, "-5", -5, "-5"),
        (BaseType.UNSIGNED_LONG, "18446744073709551615", 2**64 - 1, "18446744073709551615"),
        (BaseType.DECIMAL, "1.50", Decimal("1.50"), "1.50"),
        (
            BaseType.DATE_TIME,
            "2026-01-02T03:04:05Z",
            datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
            "2026-01-02T03:04:05Z",
        ),
        (BaseType.DATE_TIME, "0001-01-01T00:00:00Z", codec.UNKNOWN_TIME, "0001-01-01T00:00:00Z"),
        (BaseType.HEX_BINARY, "888e", b"\x88\x8e", "888E"),
        (BaseType.BASE64, "aGk=", b"hi", "aGk="),
    ]
    for base, text, value, canonical in cases:
        assert codec.decode_scalar(base, text) == value
        assert codec.encode_scalar(base, value) == canonical


def test_scalar_errors() -> None:
    for base, text in [
        (BaseType.BOOLEAN, "yes"),
        (BaseType.INT, "1.5"),
        (BaseType.DATE_TIME, "yesterday"),
        (BaseType.HEX_BINARY, "xyz"),
        (BaseType.BASE64, "!!"),
    ]:
        with pytest.raises(codec.CodecError):
            codec.decode_scalar(base, text)
    with pytest.raises(codec.CodecError):
        codec.encode_scalar(BaseType.INT, "1")
    with pytest.raises(codec.CodecError):
        codec.encode_scalar(BaseType.BOOLEAN, 1)
    with pytest.raises(codec.CodecError, match="time zone"):
        codec.encode_scalar(BaseType.DATE_TIME, datetime(2026, 1, 1))


def test_lists() -> None:
    assert codec.split_list("") == []
    assert codec.split_list(" a, b ,c") == ["a", "b", "c"]
    assert codec.split_list("[1,2],[3],4", nested_brackets=True) == ["[1,2]", "[3]", "4"]
    s = syntax(BaseType.UNSIGNED_INT, list=ListFacets(max_items=3))
    assert codec.decode(s, "1, 2") == [1, 2]
    assert codec.encode(s, [1, 2]) == "1,2"
    assert codec.encode(s, "1,2") == "1,2"
    with pytest.raises(codec.CodecError):
        codec.encode(s, 1)
    with pytest.raises(codec.CodecError):
        codec.encode(syntax(BaseType.INT), [1])


def test_problems_against_facets() -> None:
    channel = syntax(
        BaseType.UNSIGNED_INT, facets=Facets(ranges=(Range(min_inclusive=1, max_inclusive=14),))
    )
    assert codec.problems(channel, "6") == []
    assert codec.problems(channel, "0") == ["0 is outside the allowed ranges"]
    assert codec.problems(channel, "-1") == [
        "-1 is outside the unsignedInt range",
        "-1 is outside the allowed ranges",
    ]
    assert codec.problems(channel, "x") == ["'x' is not a unsignedInt"]
    stepped = syntax(
        BaseType.INT, facets=Facets(ranges=(Range(min_inclusive=0, max_inclusive=100, step=10),))
    )
    assert codec.problems(stepped, "30") == []
    assert codec.problems(stepped, "35") == ["35 is outside the allowed ranges"]
    name = syntax(BaseType.STRING, facets=Facets(sizes=(Size(max_length=3),)))
    assert codec.problems(name, "abcd") == ["length 4 is outside the allowed sizes"]
    band = syntax(
        BaseType.STRING,
        facets=Facets(enumerations=(Enumeration(value="2.4GHz"), Enumeration(value="5GHz"))),
    )
    assert codec.problems(band, "5GHz") == []
    assert codec.problems(band, "7GHz") == ["'7GHz' is not one of the enumerated values"]
    referenced = syntax(
        BaseType.STRING,
        facets=Facets(
            enumerations=(Enumeration(value="a"),), enumeration_ref=EnumerationRef(target_param="X")
        ),
    )
    assert codec.problems(referenced, "anything") == []
    oui = syntax(BaseType.STRING, facets=Facets(patterns=(Pattern(value="[0-9A-F]{6}"),)))
    assert codec.problems(oui, "00AABB") == []
    assert codec.problems(oui, "00aabb") == ["'00aabb' matches none of the patterns"]
    octets = syntax(BaseType.HEX_BINARY, facets=Facets(sizes=(Size(min_length=6, max_length=6),)))
    assert codec.problems(octets, "AABBCCDDEEFF") == []
    assert codec.problems(octets, "AABB") == ["length 2 is outside the allowed sizes"]


def test_list_problems() -> None:
    s = syntax(
        BaseType.STRING,
        list=ListFacets(min_items=1, max_items=2, sizes=(Size(max_length=8),)),
        facets=Facets(enumerations=(Enumeration(value="a"), Enumeration(value="b"))),
    )
    assert codec.problems(s, "a,b") == []
    assert codec.problems(s, "") == ["list has 0 items, at least 1 required"]
    assert (
        codec.problems(s, "a,b,a")
        == [
            "list has 3 items, at most 2 allowed",
            "list text is 5 characters, at most 8"[:0] or "list has 3 items, at most 2 allowed",
        ][:1]
    )
    assert codec.problems(s, "a,zzzzzzzz") == [
        "list text is 10 characters, at most 8",
        "item 'zzzzzzzz': 'zzzzzzzz' is not one of the enumerated values",
    ]
