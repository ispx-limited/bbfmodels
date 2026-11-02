"""Parse a published TR-106 data model document into the IR.

The parser reads the Forum's flattened ``-full.xml`` documents, in which
imports and components are already resolved, so every object carries its
parameters inline and every named data type is defined in the same file.
A document that still has ``<import>`` or ``<component>`` elements is not
supported and says so.

The published files are not always well-formed XML: descriptions carry
bare ampersands and literal ``<OUI>`` markup, and at least one attribute
value is published as ``value=\"\"\"``. ``sanitize`` repairs exactly those
before the standard library parser sees the text, so a parse failure
afterwards means the file genuinely is not a data model document.
"""

from __future__ import annotations

import re
import warnings
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from bbfmodels.ir import (
    Access,
    ActiveNotify,
    Arguments,
    BaseType,
    Command,
    DataType,
    Default,
    Document,
    Enumeration,
    EnumerationRef,
    Event,
    Facets,
    InstanceRef,
    ListFacets,
    Model,
    Object,
    Parameter,
    PathRef,
    Pattern,
    Profile,
    ProfileObject,
    Range,
    Size,
    Status,
    Syntax,
    UniqueKey,
)


class ParseError(ValueError):
    """The document cannot be read as a data model."""


class ParseWarning(UserWarning):
    """The document departs from the schema in a way the parser can work around."""


# Every element name the TR-106 schema defines. A ``<`` that does not open
# one of these, a closing tag, a comment or a processing instruction is prose
# and gets escaped.
_ELEMENTS = (
    "document",
    "import",
    "dataType",
    "model",
    "object",
    "parameter",
    "command",
    "event",
    "input",
    "output",
    "description",
    "bibliography",
    "reference",
    "template",
    "profile",
    "uniqueKey",
    "syntax",
    "list",
    "default",
    "size",
    "range",
    "enumeration",
    "enumerationRef",
    "pattern",
    "units",
    "pathRef",
    "instanceRef",
    "string",
    "int",
    "unsignedInt",
    "long",
    "unsignedLong",
    "boolean",
    "dateTime",
    "hexBinary",
    "base64",
    "decimal",
    "name",
    "title",
    "organization",
    "category",
    "date",
    "hyperlink",
    "component",
)

_TAG_START = re.compile(
    r"<(?=(?:[!?/]|(?:[A-Za-z_][\w.-]*:)?(?:" + "|".join(sorted(_ELEMENTS)) + r")[\s/>]))"
)
_BARE_AMP = re.compile(r"&(?!(?:[A-Za-z][A-Za-z0-9]*|#\d+|#x[0-9A-Fa-f]+);)")
_BASE_TYPES = {t.value for t in BaseType}


def sanitize(text: str) -> str:
    """Repair the well-formedness faults the published documents carry."""
    out: list[str] = []
    last = 0
    for match in re.finditer("<", text):
        i = match.start()
        if _TAG_START.match(text, i):
            continue
        out.append(text[last:i])
        out.append("&lt;")
        last = i + 1
    out.append(text[last:])
    repaired = "".join(out).replace('="""', '="&quot;"')
    return _BARE_AMP.sub("&amp;", repaired)


def parse_file(path: str | Path) -> Document:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return parse(text)


def parse(text: str) -> Document:
    try:
        root = ET.fromstring(sanitize(text))
    except ET.ParseError as exc:
        raise ParseError(f"not a data model document: {exc}") from exc
    if _local(root.tag) != "document":
        raise ParseError(f"root element is <{_local(root.tag)}>, expected <document>")
    return _Parser().document(root)


def _local(tag: str) -> str:
    return tag.rpartition("}")[2]


def _children(el: ET.Element, name: str) -> Iterator[ET.Element]:
    return (c for c in el if _local(c.tag) == name)


def _child(el: ET.Element, name: str) -> ET.Element | None:
    return next(_children(el, name), None)


def _attr(el: ET.Element, name: str) -> str | None:
    """A plain attribute; namespaced attributes such as ``dmr:*`` are ignored."""
    return el.get(name)


def _flag(el: ET.Element, name: str) -> bool:
    return _attr(el, name) == "true"


def _int(el: ET.Element, name: str) -> int | None:
    raw = _attr(el, name)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ParseError(f"<{_local(el.tag)} {name}={raw!r}> is not an integer") from exc


def _status(el: ET.Element) -> Status:
    raw = _attr(el, "status")
    return Status(raw) if raw else Status.CURRENT


def _text(el: ET.Element | None) -> str:
    """The description text with the authors' line structure kept.

    Indentation and trailing spaces go, runs of blank lines collapse to one,
    and the ``{{...}}`` templates stay as written: they are the Forum's own
    markup and a renderer decides what to do with them.
    """
    if el is None:
        return ""
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in "".join(el.itertext()).splitlines()]
    out: list[str] = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    while out and not out[-1]:
        out.pop()
    return "\n".join(out)


class _Parser:
    def __init__(self) -> None:
        self.data_types: dict[str, DataType] = {}

    def document(self, root: ET.Element) -> Document:
        if _child(root, "import") is not None or _child(root, "component") is not None:
            raise ParseError(
                "the document has imports or components; parse the Forum's -full.xml "
                "flattened edition instead"
            )
        spec = _attr(root, "spec") or ""
        for el in _children(root, "dataType"):
            dt = self.data_type(el)
            self.data_types[dt.name] = dt
        models = tuple(self.model(el) for el in _children(root, "model"))
        protocol: Literal["cwmp", "usp"] | None = None
        if spec.endswith("-cwmp"):
            protocol = "cwmp"
        elif spec.endswith("-usp"):
            protocol = "usp"
        return Document(
            spec=spec,
            file=_attr(root, "file"),
            protocol=protocol,
            description=_text(_child(root, "description")),
            data_types=self.data_types,
            models=models,
        )

    # -- types -------------------------------------------------------------

    def data_type(self, el: ET.Element) -> DataType:
        name = _attr(el, "name") or ""
        base = _attr(el, "base")
        list_facets = self.list_facets(_child(el, "list"))
        primitive = next((c for c in el if _local(c.tag) in _BASE_TYPES), None)
        if base is not None:
            parent = self.named(base, name)
            base_type = parent.base_type
            facets = self.facets(el).merged_over(parent.facets)
            list_facets = list_facets or parent.list
        elif primitive is not None:
            base_type = BaseType(_local(primitive.tag))
            facets = self.facets(primitive)
        else:
            raise ParseError(f"dataType {name!r} has neither a base nor a primitive type")
        return DataType(
            name=name,
            base=base,
            base_type=base_type,
            facets=facets,
            list=list_facets,
            description=_text(_child(el, "description")),
            status=_status(el),
        )

    def named(self, name: str, used_by: str) -> DataType:
        try:
            return self.data_types[name]
        except KeyError:
            raise ParseError(f"{used_by!r} uses data type {name!r}, which is not defined") from None

    def facets(self, el: ET.Element) -> Facets:
        sizes: list[Size] = []
        ranges: list[Range] = []
        enums: list[Enumeration] = []
        patterns: list[Pattern] = []
        units = path_ref = instance_ref = enum_ref = None
        for c in el:
            tag = _local(c.tag)
            if tag == "size":
                # One published document spells the attribute ``maxlength``.
                sizes.append(
                    Size(
                        min_length=_int(c, "minLength"),
                        max_length=_int(c, "maxLength")
                        if "maxLength" in c.attrib
                        else _int(c, "maxlength"),
                    )
                )
            elif tag == "range":
                ranges.append(
                    Range(
                        min_inclusive=_int(c, "minInclusive"),
                        max_inclusive=_int(c, "maxInclusive"),
                        step=_int(c, "step"),
                    )
                )
            elif tag == "enumeration":
                access = _attr(c, "access")
                enums.append(
                    Enumeration(
                        value=_attr(c, "value") or "",
                        code=_int(c, "code"),
                        access=Access(access) if access else None,
                        optional=_flag(c, "optional"),
                        status=_status(c),
                        version=_attr(c, "version"),
                        description=_text(_child(c, "description")),
                    )
                )
            elif tag == "pattern":
                patterns.append(
                    Pattern(
                        value=_attr(c, "value") or "",
                        status=_status(c),
                        version=_attr(c, "version"),
                        description=_text(_child(c, "description")),
                    )
                )
            elif tag == "units":
                units = _attr(c, "value")
            elif tag == "pathRef":
                path_ref = PathRef(
                    ref_type=_attr(c, "refType") or "strong",  # type: ignore[arg-type]
                    target_parent=_attr(c, "targetParent"),
                    target_type=_attr(c, "targetType") or "row",
                    target_data_type=_attr(c, "targetDataType"),
                )
            elif tag == "instanceRef":
                instance_ref = InstanceRef(
                    ref_type=_attr(c, "refType") or "strong",  # type: ignore[arg-type]
                    target_parent=_attr(c, "targetParent"),
                )
            elif tag == "enumerationRef":
                enum_ref = EnumerationRef(
                    target_param=_attr(c, "targetParam") or "",
                    null_value=_attr(c, "nullValue"),
                )
        return Facets(
            sizes=tuple(sizes),
            ranges=tuple(ranges),
            enumerations=tuple(enums),
            patterns=tuple(patterns),
            units=units,
            path_ref=path_ref,
            instance_ref=instance_ref,
            enumeration_ref=enum_ref,
        )

    def list_facets(self, el: ET.Element | None) -> ListFacets | None:
        if el is None:
            return None
        return ListFacets(
            min_items=_int(el, "minItems"),
            max_items=_int(el, "maxItems"),
            sizes=tuple(
                Size(min_length=_int(s, "minLength"), max_length=_int(s, "maxLength"))
                for s in _children(el, "size")
            ),
            nested_brackets=_attr(el, "nestedBrackets") == "required",
        )

    def syntax(self, el: ET.Element, owner: str) -> Syntax:
        base_type: BaseType | None = None
        data_type: str | None = None
        facets = Facets()
        list_facets = self.list_facets(_child(el, "list"))
        default = None
        for c in el:
            tag = _local(c.tag)
            if tag == "dataType":
                # ``ref`` uses the named type as is; ``base`` derives an
                # anonymous type from it. Both resolve the same way here.
                data_type = _attr(c, "ref") or _attr(c, "base") or ""
                named = self.named(data_type, owner)
                base_type = named.base_type
                facets = self.facets(c).merged_over(named.facets)
                list_facets = list_facets or named.list
            elif tag in _BASE_TYPES:
                base_type = BaseType(tag)
                facets = self.facets(c)
            elif tag == "default":
                default = Default(
                    kind=_attr(c, "type") or "object",  # type: ignore[arg-type]
                    value=_attr(c, "value") or "",
                    status=_status(c),
                )
        if base_type is None:
            # Vendor documents captured from devices sometimes publish an
            # empty <syntax/>. The schema forbids it; a string loses nothing.
            warnings.warn(
                f"{owner} has a syntax without a type; treated as a string",
                ParseWarning,
                stacklevel=2,
            )
            base_type = BaseType.STRING
        return Syntax(
            base_type=base_type,
            data_type=data_type,
            facets=facets,
            list=list_facets,
            hidden=_flag(el, "hidden"),
            secured=_flag(el, "secured"),
            command=_flag(el, "command"),
            default=default,
        )

    # -- objects -----------------------------------------------------------

    def parameter(self, el: ET.Element, owner: str) -> Parameter:
        name = _attr(el, "name") or ""
        syntax_el = _child(el, "syntax")
        if syntax_el is None:
            raise ParseError(f"parameter {owner}{name} has no syntax")
        access = _attr(el, "access")
        notify = _attr(el, "activeNotify")
        mandatory = _attr(el, "mandatory")
        return Parameter(
            name=name,
            access=Access(access) if access else None,
            description=_text(_child(el, "description")),
            version=_attr(el, "version"),
            status=_status(el),
            active_notify=ActiveNotify(notify) if notify else ActiveNotify.NORMAL,
            forced_inform=_flag(el, "forcedInform"),
            mandatory=None if mandatory is None else mandatory == "true",
            syntax=self.syntax(syntax_el, owner + name),
        )

    def object(self, el: ET.Element, prefix: str = "") -> Object:
        path = _attr(el, "name") or ""
        full = prefix + path
        max_raw = _attr(el, "maxEntries")
        min_raw = _int(el, "minEntries")
        access = _attr(el, "access")
        return Object(
            path=path,
            access=Access(access) if access else None,
            min_entries=1 if min_raw is None else min_raw,
            max_entries=None if max_raw == "unbounded" else (int(max_raw) if max_raw else 1),
            num_entries_parameter=_attr(el, "numEntriesParameter"),
            enable_parameter=_attr(el, "enableParameter"),
            discriminator_parameter=_attr(el, "discriminatorParameter"),
            mount_type=_attr(el, "mountType"),
            unique_keys=tuple(
                UniqueKey(
                    functional=_attr(k, "functional") != "false",
                    parameters=tuple(_attr(p, "ref") or "" for p in _children(k, "parameter")),
                )
                for k in _children(el, "uniqueKey")
            ),
            description=_text(_child(el, "description")),
            version=_attr(el, "version"),
            status=_status(el),
            parameters={
                p.name: p for p in (self.parameter(c, full) for c in _children(el, "parameter"))
            },
            commands={c.name: c for c in (self.command(e, full) for e in _children(el, "command"))},
            events={e.name: e for e in (self.event(x, full) for x in _children(el, "event"))},
        )

    def arguments(self, el: ET.Element | None, owner: str) -> Arguments:
        if el is None:
            return Arguments()
        return Arguments(
            parameters={
                p.name: p for p in (self.parameter(c, owner) for c in _children(el, "parameter"))
            },
            objects={o.path: o for o in (self.object(c, owner) for c in _children(el, "object"))},
        )

    def command(self, el: ET.Element, owner: str) -> Command:
        name = _attr(el, "name") or ""
        return Command(
            name=name,
            is_async=_flag(el, "async"),
            description=_text(_child(el, "description")),
            version=_attr(el, "version"),
            status=_status(el),
            input=self.arguments(_child(el, "input"), f"{owner}{name} input "),
            output=self.arguments(_child(el, "output"), f"{owner}{name} output "),
        )

    def event(self, el: ET.Element, owner: str) -> Event:
        name = _attr(el, "name") or ""
        return Event(
            name=name,
            description=_text(_child(el, "description")),
            version=_attr(el, "version"),
            status=_status(el),
            arguments=self.arguments(el, f"{owner}{name} "),
        )

    # -- models ------------------------------------------------------------

    def model(self, el: ET.Element) -> Model:
        name = _attr(el, "name") or ""
        objects: dict[str, Object] = {}
        for c in _children(el, "object"):
            if _attr(c, "name"):
                obj = self.object(c)
                objects[obj.path] = obj
        profiles = {p.name: p for p in (self.profile(c) for c in _children(el, "profile"))}
        return Model(
            name=name,
            is_service=_flag(el, "isService"),
            description=_text(_child(el, "description")),
            parameters={
                p.name: p
                for p in (self.parameter(c, name + " ") for c in _children(el, "parameter"))
            },
            objects=objects,
            profiles=profiles,
        )

    def profile(self, el: ET.Element) -> Profile:
        extends = _attr(el, "extends")
        objects: dict[str, ProfileObject] = {}
        for o in _children(el, "object"):
            ref = _attr(o, "ref") or ""
            objects[ref] = ProfileObject(
                path=ref,
                requirement=_attr(o, "requirement") or "present",
                parameters={
                    _attr(p, "ref") or "": _attr(p, "requirement") or ""
                    for p in _children(o, "parameter")
                },
                commands={
                    _attr(p, "ref") or "": _attr(p, "requirement") or ""
                    for p in _children(o, "command")
                },
                events={
                    _attr(p, "ref") or "": _attr(p, "requirement") or ""
                    for p in _children(o, "event")
                },
            )
        return Profile(
            name=_attr(el, "name") or "",
            base=_attr(el, "base"),
            extends=tuple(extends.split()) if extends else (),
            version=_attr(el, "version"),
            status=_status(el),
            description=_text(_child(el, "description")),
            parameters={
                _attr(p, "ref") or "": _attr(p, "requirement") or ""
                for p in _children(el, "parameter")
            },
            objects=objects,
        )
