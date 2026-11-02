"""The base class and field types of generated Python models.

A generated model is a pydantic model per object of a data model, with one
field per parameter, one field per child object and a ``dict[int, Child]``
per table. ``Model`` gives every generated class the conversions the wire
needs: ``from_flat`` builds an instance from a device's path and value
pairs, ``flatten`` writes it back out as text, ``problems`` checks it
against the schema's facets.

Parsing is lenient on purpose: values are coerced to their Python type, and
facet violations are reported by ``problems`` rather than rejected, because
a real device returns out-of-range values and vendor enumerations and a
model that refuses them cannot hold what the device said.
"""

from __future__ import annotations

import base64
import gzip
import importlib.resources
import typing
from dataclasses import dataclass
from typing import Annotated, Any, TypeVar, get_args, get_origin

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer

from bbfmodels import codec
from bbfmodels.ir import BaseType, Document
from bbfmodels.schema import Schema

T = TypeVar("T")


@dataclass(frozen=True)
class Param:
    """Field metadata: how a parameter is written on the wire."""

    base_type: BaseType
    list: bool = False


def _split(value: object) -> object:
    return codec.split_list(value) if isinstance(value, str) else value


def _from_hex(value: object) -> object:
    return bytes.fromhex(value) if isinstance(value, str) else value


def _from_base64(value: object) -> object:
    return base64.b64decode(value) if isinstance(value, str) else value


def _bool(value: object) -> object:
    if isinstance(value, str):
        return codec.decode_scalar(BaseType.BOOLEAN, value)
    return value


CommaList = Annotated[list[T], BeforeValidator(_split)]
HexBinary = Annotated[
    bytes, BeforeValidator(_from_hex), PlainSerializer(lambda b: b.hex().upper(), return_type=str)
]
Base64Binary = Annotated[
    bytes,
    BeforeValidator(_from_base64),
    PlainSerializer(lambda b: base64.b64encode(b).decode("ascii"), return_type=str),
]
Boolean = Annotated[bool, BeforeValidator(_bool)]


class Model(BaseModel):
    """Base of every generated object class."""

    model_config = ConfigDict(extra="allow", defer_build=True, populate_by_name=True)

    # Dunder names so no Forum name can collide with them: the schema path of
    # the object, ``Device.WiFi.Radio.{i}.``, and the package holding the IR
    # the class was generated from.
    __bbf_path__ = ""
    __bbf_package__ = ""

    @classmethod
    def schema_of(cls) -> Schema:
        return load_schema(cls.__bbf_package__)

    @classmethod
    def from_flat(cls, values: typing.Mapping[str, str], prefix: str | None = None) -> typing.Self:
        """An instance from path and text pairs.

        Paths are relative to the object (``Radio.1.Channel``) or start with
        ``prefix``, the object's data path (``Device.WiFi.``). The prefix
        defaults to the schema path for an object with no table above it; a
        service model's root is a table, so its instance path is given:
        ``VoiceService.from_flat(values, "Device.Services.VoiceService.1.")``.
        """
        nested: dict[str, Any] = {}
        if prefix is None and "{i}" not in cls.__bbf_path__:
            prefix = cls.__bbf_path__
        for path, text in values.items():
            rel = path[len(prefix) :] if prefix and path.startswith(prefix) else path
            _place(cls, nested, rel.split("."), text)
        return cls.model_validate(nested)

    def flatten(self, prefix: str | None = None) -> dict[str, str]:
        """Every parameter as path and wire text.

        ``prefix`` is the data path of this object, ``Device.WiFi.Radio.1.``;
        it defaults to the schema path, which is only meaningful for objects
        without a table above them.
        """
        out: dict[str, str] = {}
        base = self.__bbf_path__ if prefix is None else prefix
        for name, info in type(self).model_fields.items():
            value = getattr(self, name)
            if value is None:
                continue
            wire = info.alias or name
            param = _param_of(info.metadata)
            if param is not None:
                out[base + wire] = _encode(param, value)
            elif isinstance(value, Model):
                out.update(value.flatten(base + wire + "."))
            elif isinstance(value, dict):
                for number, instance in value.items():
                    out.update(instance.flatten(f"{base}{wire}.{number}."))
        for name, value in (self.__pydantic_extra__ or {}).items():
            out.update(_flatten_unknown(base + name, value))
        return out

    def problems(self, prefix: str | None = None) -> list[tuple[str, str]]:
        """Every facet violation, as data path and message.

        Each value is checked against its parameter's syntax in the shipped
        schema; ``prefix`` only names the data path in the report and
        defaults to the schema path with ``1`` for every instance, so a table
        root such as ``VoiceService.{i}.`` is reported as its first instance.
        """
        if prefix is None:
            prefix = self.__bbf_path__.replace("{i}", "1")
        schema = self.schema_of()
        found: list[tuple[str, str]] = []
        for name, info in type(self).model_fields.items():
            value = getattr(self, name)
            if value is None:
                continue
            wire = info.alias or name
            param = _param_of(info.metadata)
            if param is not None:
                syntax = schema.parameter(self.__bbf_path__ + wire).syntax
                found.extend(
                    (prefix + wire, p) for p in codec.problems(syntax, _encode(param, value))
                )
            elif isinstance(value, Model):
                found.extend(value.problems(f"{prefix}{wire}."))
            elif isinstance(value, dict):
                for number, instance in value.items():
                    found.extend(instance.problems(f"{prefix}{wire}.{number}."))
        return found


def _param_of(metadata: list[Any]) -> Param | None:
    return next((m for m in metadata if isinstance(m, Param)), None)


def _encode(param: Param, value: Any) -> str:
    if param.list:
        return codec.join_list([codec.encode_scalar(param.base_type, v) for v in value])
    return codec.encode_scalar(param.base_type, value)


def _flatten_unknown(path: str, value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        out: dict[str, str] = {}
        for key, sub in value.items():
            out.update(_flatten_unknown(f"{path}.{key}", sub))
        return out
    return {path: value if isinstance(value, str) else str(value)}


def _field_target(cls: type[Model], name: str) -> tuple[str, type[Model] | None]:
    """What a wire name holds: ``param``, ``child`` or ``table``, and the model class if any.

    ``name`` is the Forum's name; a field whose Python name had to differ
    carries it as its alias.
    """
    info = cls.model_fields.get(name)
    if info is None or info.alias is not None:
        info = next((i for i in cls.model_fields.values() if i.alias == name), None)
    if info is None:
        return "unknown", None
    if _param_of(info.metadata) is not None:
        return "param", None
    annotation = info.annotation
    for arg in (annotation, *get_args(annotation)):
        if isinstance(arg, type) and issubclass(arg, Model):
            return "child", arg
        if get_origin(arg) is dict:
            _, item = get_args(arg)
            if isinstance(item, type) and issubclass(item, Model):
                return "table", item
    return "unknown", None


def _place(cls: type[Model] | None, into: dict[str, Any], segments: list[str], text: str) -> None:
    """Put one wire value into the nested dict the model validates from.

    Segments the class does not know go in as plain dicts, with a numeric
    segment taken as an instance number, so unknown objects keep their shape.
    """
    head, rest = segments[0], segments[1:]
    if not rest:
        into[head] = text
        return
    kind, target = _field_target(cls, head) if cls is not None else ("unknown", None)
    if kind == "table" or (kind == "unknown" and rest[0].isdigit()):
        table = into.setdefault(head, {})
        key: int | str = int(rest[0]) if kind == "table" else rest[0]
        if len(rest) == 1:
            table[key] = text
        else:
            _place(target, table.setdefault(key, {}), rest[1:], text)
        return
    _place(target, into.setdefault(head, {}), rest, text)


_schemas: dict[str, Schema] = {}


def load_schema(package: str) -> Schema:
    """The schema of a generated package, read from the IR it ships with."""
    if package not in _schemas:
        data = importlib.resources.files(package).joinpath("ir.json.gz").read_bytes()
        doc = Document.model_validate_json(gzip.decompress(data))
        schema = Schema()
        # A service model is indexed as the document writes it, unmounted,
        # which is how the generated classes name their paths.
        schema.add(doc, mount="" if all(m.is_service for m in doc.models) else None)
        _schemas[package] = schema
    return _schemas[package]
