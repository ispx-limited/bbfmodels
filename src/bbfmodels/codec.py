"""Convert between wire text and Python values, and validate against facets.

CWMP and USP carry every parameter value as text. TR-106 defines how each
base type is written: integers in decimal, booleans as ``true``/``false``
or ``1``/``0``, dates in ISO 8601 with the Unknown Time as
``0001-01-01T00:00:00Z``, binary as upper-case hex or base64, and lists as
comma-separated items of the base type. ``decode`` and ``encode`` are the
two directions of that rule; ``problems`` checks a value against the
syntax's facets and reports every violation it finds.
"""

from __future__ import annotations

import base64
import binascii
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from bbfmodels.ir import BaseType, Range, Size, Syntax

Scalar = str | int | bool | datetime | bytes | Decimal
Value = Scalar | list[Scalar]

UNKNOWN_TIME = datetime(1, 1, 1, tzinfo=UTC)

_BOUNDS = {
    BaseType.INT: (-(2**31), 2**31 - 1),
    BaseType.UNSIGNED_INT: (0, 2**32 - 1),
    BaseType.LONG: (-(2**63), 2**63 - 1),
    BaseType.UNSIGNED_LONG: (0, 2**64 - 1),
}


class CodecError(ValueError):
    """The text is not a value of the parameter's type."""


# -- scalars ----------------------------------------------------------------


def decode_scalar(base_type: BaseType, text: str) -> Scalar:
    try:
        match base_type:
            case BaseType.STRING:
                return text
            case BaseType.BOOLEAN:
                if text in ("1", "true"):
                    return True
                if text in ("0", "false"):
                    return False
                raise CodecError(f"{text!r} is not a boolean")
            case BaseType.INT | BaseType.UNSIGNED_INT | BaseType.LONG | BaseType.UNSIGNED_LONG:
                return int(text)
            case BaseType.DECIMAL:
                return Decimal(text)
            case BaseType.DATE_TIME:
                return datetime.fromisoformat(text.replace("Z", "+00:00"))
            case BaseType.HEX_BINARY:
                return bytes.fromhex(text)
            case BaseType.BASE64:
                return base64.b64decode(text, validate=True)
    except (ValueError, InvalidOperation, binascii.Error) as exc:
        raise CodecError(f"{text!r} is not a {base_type.value}") from exc
    raise CodecError(f"unknown base type {base_type!r}")


def encode_scalar(base_type: BaseType, value: Scalar) -> str:
    match base_type:
        case BaseType.STRING:
            if isinstance(value, str):
                return value
        case BaseType.BOOLEAN:
            if isinstance(value, bool):
                return "true" if value else "false"
        case BaseType.INT | BaseType.UNSIGNED_INT | BaseType.LONG | BaseType.UNSIGNED_LONG:
            if isinstance(value, int) and not isinstance(value, bool):
                return str(value)
        case BaseType.DECIMAL:
            if isinstance(value, Decimal | int) and not isinstance(value, bool):
                return str(value)
        case BaseType.DATE_TIME:
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    raise CodecError("a dateTime needs a time zone")
                text = value.astimezone(UTC).isoformat()
                return text.replace("+00:00", "Z")
        case BaseType.HEX_BINARY:
            if isinstance(value, bytes):
                return value.hex().upper()
        case BaseType.BASE64:
            if isinstance(value, bytes):
                return base64.b64encode(value).decode("ascii")
    raise CodecError(f"{value!r} cannot be written as a {base_type.value}")


# -- lists ------------------------------------------------------------------


def split_list(text: str, nested_brackets: bool = False) -> list[str]:
    """Items of a comma-separated list, whitespace around items removed.

    With ``nested_brackets`` an item may itself be a bracketed list, as in
    ``[a,b],[c]``, and the split happens only at the top level.
    """
    if text.strip() == "":
        return []
    if not nested_brackets:
        return [item.strip() for item in text.split(",")]
    items: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(text):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        elif ch == "," and depth == 0:
            items.append(text[start:i].strip())
            start = i + 1
    items.append(text[start:].strip())
    return items


def join_list(items: list[str]) -> str:
    return ",".join(items)


# -- syntax -----------------------------------------------------------------


def decode(syntax: Syntax, text: str) -> Value:
    """The Python value of a parameter's wire text."""
    if syntax.list is not None:
        items = split_list(text, syntax.list.nested_brackets)
        return [decode_scalar(syntax.base_type, item) for item in items]
    return decode_scalar(syntax.base_type, text)


def encode(syntax: Syntax, value: Value) -> str:
    """The wire text of a Python value for a parameter."""
    if syntax.list is not None:
        if isinstance(value, list):
            return join_list([encode_scalar(syntax.base_type, item) for item in value])
        if isinstance(value, str):
            # A list given as text is passed through as the caller wrote it.
            return value
        raise CodecError(f"{value!r} is not a list")
    if isinstance(value, list):
        raise CodecError("a list was given for a single value")
    return encode_scalar(syntax.base_type, value)


def problems(syntax: Syntax, text: str) -> list[str]:
    """Every way the wire text violates the syntax; empty means valid."""
    found: list[str] = []
    if syntax.list is not None:
        items = split_list(text, syntax.list.nested_brackets)
        lf = syntax.list
        if lf.min_items is not None and len(items) < lf.min_items:
            found.append(f"list has {len(items)} items, at least {lf.min_items} required")
        if lf.max_items is not None and len(items) > lf.max_items:
            found.append(f"list has {len(items)} items, at most {lf.max_items} allowed")
        for size in lf.sizes:
            if size.max_length is not None and len(text) > size.max_length:
                found.append(f"list text is {len(text)} characters, at most {size.max_length}")
        for item in items:
            found.extend(f"item {item!r}: {p}" for p in _scalar_problems(syntax, item))
        return found
    return _scalar_problems(syntax, text)


def _scalar_problems(syntax: Syntax, text: str) -> list[str]:
    try:
        value = decode_scalar(syntax.base_type, text)
    except CodecError as exc:
        return [str(exc)]
    f = syntax.facets
    found: list[str] = []
    if isinstance(value, int) and not isinstance(value, bool):
        low, high = _BOUNDS.get(syntax.base_type, (None, None))
        if low is not None and high is not None and not low <= value <= high:
            found.append(f"{value} is outside the {syntax.base_type.value} range")
        if f.ranges and not any(_in_range(value, r) for r in f.ranges):
            found.append(f"{value} is outside the allowed ranges")
    if (
        isinstance(value, str | bytes)
        and f.sizes
        and not any(_in_size(len(value), s) for s in f.sizes)
    ):
        found.append(f"length {len(value)} is outside the allowed sizes")
    if isinstance(value, str):
        if (
            f.enumerations
            and f.enumeration_ref is None
            and value not in {e.value for e in f.enumerations}
        ):
            found.append(f"{value!r} is not one of the enumerated values")
        if f.patterns and not any(_matches(p.value, value) for p in f.patterns):
            found.append(f"{value!r} matches none of the patterns")
    return found


def _in_range(value: int, r: Range) -> bool:
    if r.min_inclusive is not None and value < r.min_inclusive:
        return False
    if r.max_inclusive is not None and value > r.max_inclusive:
        return False
    return not (r.step and (value - (r.min_inclusive or 0)) % r.step)


def _in_size(length: int, s: Size) -> bool:
    if s.min_length is not None and length < s.min_length:
        return False
    return s.max_length is None or length <= s.max_length


_pattern_cache: dict[str, re.Pattern[str] | None] = {}


def _matches(pattern: str, value: str) -> bool:
    # TR-106 patterns are XML Schema regular expressions, which are implicitly
    # anchored. Python's syntax covers the ones the Forum publishes; a pattern
    # Python cannot compile is treated as matching rather than rejecting
    # every value.
    if pattern not in _pattern_cache:
        try:
            _pattern_cache[pattern] = re.compile(pattern)
        except re.error:
            _pattern_cache[pattern] = None
    compiled = _pattern_cache[pattern]
    return compiled is None or compiled.fullmatch(value) is not None
