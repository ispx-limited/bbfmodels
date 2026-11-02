"""Render the Forum's description markup as plain prose.

Descriptions in the published documents carry a template language:
``{{param|Name}}`` names a parameter, ``{{enum|Up}}`` a value,
``{{units}}`` the parameter's own units, ``{{list}}`` says the value is a
comma-separated list, ``{{bibref|RFC2863}}`` cites a reference, and so on.
The IR keeps the markup as written, because it is the Forum's text. The
emitters that write documentation a person reads, the TypeScript and Go
doc comments and the JSON Schema descriptions, render it through
``render`` so ``{{units}}`` becomes ``seconds`` and ``{{list}}`` becomes a
sentence.

The rendering is a reading, not the Forum's own report tool: templates
that need the whole document (``{{template|...}}``, ``{{section|...}}``)
are dropped, and anything unknown is left as written so nothing is lost.
"""

from __future__ import annotations

import re

from bbfmodels.ir import DataType, Syntax

# Arguments may carry a {i} placeholder, as in {{object|Device.WiFi.Radio.{i}.}}.
_TEMPLATE = re.compile(r"\{\{([a-zA-Z]+)((?:\|(?:[^{}]|\{i\})*)*)\}\}", re.S)
_QUOTES = re.compile(r"'{2,3}")
_SPACES = re.compile(r"[ \t]{2,}")
_SPACE_BEFORE_PUNCT = re.compile(r" +([.,;:])")
_BLANK_RUN = re.compile(r"\n(?:[ \t]*\n){2,}")


def render(
    text: str,
    syntax: Syntax | None = None,
    data_types: dict[str, DataType] | None = None,
    *,
    parameter: str | None = None,
    object: str | None = None,
) -> str:
    """The description as prose, with the templates resolved against the syntax.

    ``parameter`` and ``object`` are the names a bare ``{{param}}`` or
    ``{{object}}`` refers to: the parameter being described and the object
    that holds it, which is how the Forum's own report tool reads them.
    """
    if not text:
        return ""
    subjects = {"param": parameter, "object": object}
    out = text
    for _ in range(6):  # nested templates resolve inner first; six levels is far past the deepest
        new = _TEMPLATE.sub(
            lambda m: _expand(m.group(1), _args(m.group(2)), syntax, data_types, subjects), out
        )
        if new == out:
            break
        out = new
    out = _QUOTES.sub("", out)
    out = _SPACE_BEFORE_PUNCT.sub(r"\1", _SPACES.sub(" ", out))
    out = "\n".join(line.rstrip() for line in out.split("\n"))
    # A dropped template can leave an empty paragraph behind; one blank line is the most kept.
    return _BLANK_RUN.sub("\n\n", out).strip()


def _args(raw: str) -> list[str]:
    return [a.strip() for a in raw.split("|")[1:]] if raw else []


def _expand(
    name: str,
    args: list[str],
    syntax: Syntax | None,
    data_types: dict[str, DataType] | None,
    subjects: dict[str, str | None],
) -> str:
    first = args[0] if args else ""
    f = syntax.facets if syntax else None
    match name:
        case "param":
            return first or subjects["param"] or "this parameter"
        case "object":
            return first.rstrip(".") or subjects["object"] or "this object"
        case "command":
            return first or "this command"
        case "event":
            return first or "this event"
        case "enum":
            if first:
                return f'"{first}"'
            if f and f.enumerations:
                return "Enumeration of: " + ", ".join(e.value for e in f.enumerations) + "."
            return ""
        case "units":
            return (f.units if f and f.units else None) or "units"
        case "true" | "false" | "null":
            return name
        case "empty":
            return "an empty string"
        case "numentries":
            return "The number of entries in the table."
        case "list":
            tail = f", {first}" if first else ""
            return f"Comma-separated list{tail}."
        case "nolist" | "noreference" | "nopattern" | "nokeys" | "template" | "section":
            return ""
        case "reference":
            return f"A reference to {first}." if first else "A path reference."
        case "bibref":
            return f"[{' '.join(a for a in args if a)}]" if args else ""
        case "datatype":
            if syntax and syntax.data_type:
                dt = (data_types or {}).get(syntax.data_type)
                if first == "expand" and dt and dt.description:
                    return dt.description
                return syntax.data_type
            return ""
        case "deprecated" | "obsoleted" | "deleted":
            version = args[0] if args else ""
            reason = args[1] if len(args) > 1 else ""
            head = f"{name.capitalize()} in {version}" if version else name.capitalize()
            return f"{head}: {reason}" if reason else f"{head}."
        case "pattern":
            if first:
                return f"the pattern {first}"
            if f and f.patterns:
                return "Pattern: " + " or ".join(p.value for p in f.patterns if p.value) + "."
            return ""
        case "range":
            if f and f.ranges:
                parts = []
                for r in f.ranges:
                    low = "" if r.min_inclusive is None else str(r.min_inclusive)
                    high = "" if r.max_inclusive is None else str(r.max_inclusive)
                    parts.append(f"{low} to {high}".strip())
                return "Range: " + ", ".join(parts) + "."
            return ""
        case "keys":
            return ""
        case "hidden":
            return "The value is hidden when read."
        case "maxval":
            return "the maximum value"
    return "{{" + name + ("|" + "|".join(args) if args else "") + "}}"
