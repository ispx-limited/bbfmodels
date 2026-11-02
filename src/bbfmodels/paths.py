"""Typed paths: build correct parameter paths with autocomplete, no models.

Most code that talks to an ACS or a USP controller never builds a tree of
values. It asks an API for ``Device.WiFi.SSID.1.SSID`` by name and gets a
string back. A typed path makes that name a chain of attributes an editor
completes and a type checker verifies, and ``str()`` of the chain is the
path::

    from bbfmodels.tr181_cwmp.paths import Device

    str(Device.WiFi.SSID[1].SSID)        # 'Device.WiFi.SSID.1.SSID'
    Device.WiFi.Radio[2].Channel.definition.syntax.base_type   # unsignedInt
    str(Device.WiFi.Radio)               # 'Device.WiFi.Radio.' (the table)
    Device.WiFi.Radio.search             # 'Device.WiFi.Radio.*.' (a USP search path)

At runtime one generic class walks the package's schema, so nothing is
generated beyond a stub file (``paths.pyi``) that gives editors the names
and the value types. An unknown name is an ``AttributeError``; a vendor
parameter the schema does not list is reached explicitly with ``child()``.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Generic, TypeVar

from bbfmodels.ir import Object, Parameter
from bbfmodels.schema import Schema

T = TypeVar("T")


def identifier(name: str) -> str:
    """A Forum name as a Python identifier.

    Forum names are identifiers already except in vendor documents, where a
    name may start with a digit (``11kRSSIHighThresholdOffset``) or carry a
    hyphen. A leading digit gets an ``N`` in front, because a leading
    underscore would make pydantic treat a model field as private, and any
    other character Python rejects becomes an underscore. Models keep the
    Forum name as the field's alias; paths map the identifier back to it.
    """
    out = re.sub(r"\W", "_", name)
    return "N" + out if out[:1].isdigit() else out


class _Path:
    __slots__ = ("_data", "_schema", "_schema_path")

    def __init__(self, schema: Callable[[], Schema], data: str, schema_path: str) -> None:
        self._schema = schema
        self._data = data
        self._schema_path = schema_path

    def __str__(self) -> str:
        return self._data

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._data!r})"

    def __eq__(self, other: object) -> bool:
        return str(self) == str(other) if isinstance(other, _Path | str) else NotImplemented

    def __hash__(self) -> int:
        return hash(self._data)

    @property
    def path(self) -> str:
        """The data path, ``Device.WiFi.Radio.1.Channel``."""
        return self._data

    @property
    def schema_path(self) -> str:
        """The path with ``{i}`` for every instance, ``Device.WiFi.Radio.{i}.Channel``."""
        return self._schema_path


class ParamPath(_Path, Generic[T]):
    """A parameter. ``T`` is the Python type of its value, for the reader only."""

    __slots__ = ()

    @property
    def definition(self) -> Parameter:
        return self._schema().parameter(self._schema_path)


class ObjectPathBase(_Path):
    """An object, or one instance of a table, without attribute access.

    The generated stubs derive their classes from this one and declare each
    member explicitly, so a type checker rejects a name the model does not
    have. ``ObjectPath`` adds the attribute access the interpreter uses.
    """

    __slots__ = ()

    @property
    def definition(self) -> Object:
        return self._schema().object(self._schema_path)

    def child(self, name: str) -> ObjectPath | TablePath[ObjectPath] | ParamPath[object]:
        """The parameter or object called ``name`` under this object, schema-defined or not.

        A name the schema does not define is taken as a parameter, which is
        how a vendor's ``X_`` parameter is reached when its document was not
        generated.
        """
        schema = self._schema()
        if self._schema_path + name + "." in schema.objects:
            return ObjectPath(self._schema, self._data + name + ".", self._schema_path + name + ".")
        if self._schema_path + name + ".{i}." in schema.objects:
            return TablePath(
                self._schema, self._data + name + ".", self._schema_path + name + ".{i}."
            )
        return ParamPath(self._schema, self._data + name, self._schema_path + name)


class ObjectPath(ObjectPathBase):
    """An object whose members are reached as attributes."""

    __slots__ = ()

    def __getattr__(self, name: str) -> ObjectPath | TablePath[ObjectPath] | ParamPath[object]:
        if name.startswith("_"):
            raise AttributeError(name)
        obj = self.definition
        schema = self._schema()
        for forum in (*obj.parameters, *(c.name for c in schema.children(self._schema_path))):
            if forum == name or identifier(forum) == name:
                return self.child(forum)
        raise AttributeError(f"{self._schema_path} has no parameter or object {name!r}")


class TablePath(_Path, Generic[T]):
    """A multi-instance object. ``str()`` is the partial path of the table itself."""

    __slots__ = ()

    def __getitem__(self, instance: int) -> T:
        if not isinstance(instance, int) or isinstance(instance, bool) or instance < 1:
            raise TypeError("an instance number is a positive int")
        path = ObjectPath(self._schema, f"{self._data}{instance}.", self._schema_path)
        return path  # type: ignore[return-value]

    @property
    def definition(self) -> Object:
        return self._schema().object(self._schema_path)

    @property
    def search(self) -> str:
        """The USP search path for every instance, ``Device.WiFi.Radio.*.``."""
        return self._data + "*."
