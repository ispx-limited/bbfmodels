"""A schema: the objects of one or more documents, addressable by path.

A device's tree is described by several documents at once: the root model
(TR-181 or TR-098), service models mounted under ``Services.`` (TR-104
voice, TR-135 set-top box) and a vendor's extensions. ``Schema`` indexes
all of them by full schema path, the path with ``{i}`` in place of every
instance number, and resolves data paths (``Device.WiFi.Radio.1.Channel``)
to the schema node they belong to.
"""

from __future__ import annotations

from dataclasses import dataclass

from bbfmodels.ir import DataType, Document, Object, Parameter


class UnknownPath(KeyError):
    """The path names nothing the schema knows."""


@dataclass(frozen=True)
class Resolved:
    """What a data path points at."""

    object: Object
    parameter: Parameter | None
    instances: tuple[int, ...]

    @property
    def schema_path(self) -> str:
        return self.object.path + (self.parameter.name if self.parameter else "")


class Schema:
    def __init__(self) -> None:
        self.documents: list[Document] = []
        self.objects: dict[str, Object] = {}
        self.data_types: dict[str, DataType] = {}

    @classmethod
    def from_documents(cls, *documents: Document) -> Schema:
        schema = cls()
        for doc in documents:
            schema.add(doc)
        return schema

    def add(self, document: Document, mount: str | None = None) -> None:
        """Index a document's objects.

        A service model (``VoiceService:2.0``) is mounted under ``mount``,
        or under the ``Services.`` object of the root model already added,
        so its objects get the full path they have on a device.
        """
        self.documents.append(document)
        self.data_types.update(document.data_types)
        for model in document.models:
            prefix = ""
            if model.is_service:
                prefix = mount if mount is not None else self._services_mount()
            for obj in model.objects.values():
                mounted = obj.model_copy(update={"path": prefix + obj.path}) if prefix else obj
                self.objects[mounted.path] = mounted

    def _services_mount(self) -> str:
        roots = [p for p in self.objects if p.count(".") == 1]
        if len(roots) != 1:
            raise ValueError("a service model needs a mount point or exactly one root model")
        return roots[0] + "Services."

    # -- lookup ----------------------------------------------------------

    @property
    def roots(self) -> list[Object]:
        return [o for p, o in self.objects.items() if p.count(".") == 1]

    def object(self, schema_path: str) -> Object:
        try:
            return self.objects[schema_path]
        except KeyError:
            raise UnknownPath(schema_path) from None

    def parameter(self, schema_path: str) -> Parameter:
        obj_path, _, name = schema_path.rpartition(".")
        obj = self.object(obj_path + ".")
        try:
            return obj.parameters[name]
        except KeyError:
            raise UnknownPath(schema_path) from None

    def children(self, schema_path: str) -> list[Object]:
        """The objects directly under an object, tables included."""
        return [o for o in self.objects.values() if o.parent_path == schema_path]

    def resolve(self, data_path: str) -> Resolved:
        """The schema node a data path points at, and the instance numbers in it.

        A path ending in ``.`` is an object; otherwise the last segment is a
        parameter. A table may be addressed without an instance
        (``Device.WiFi.Radio.``) or with the literal ``{i}``, so a schema path
        resolves too. Raises ``UnknownPath`` for anything the schema does not
        define, including a vendor extension it was not given.
        """
        is_object = data_path.endswith(".")
        segments = data_path.rstrip(".").split(".")
        param_name = None if is_object else segments.pop()
        path = ""
        instances: list[int] = []
        pending = False  # a table was named and its instance has not been seen yet
        for seg in segments:
            if pending:
                if seg == "{i}":
                    pending = False
                elif seg.isdigit():
                    instances.append(int(seg))
                    pending = False
                else:
                    raise UnknownPath(data_path)
            elif path + seg + "." in self.objects:
                path += seg + "."
            elif path + seg + ".{i}." in self.objects:
                path += seg + ".{i}."
                pending = True
            else:
                raise UnknownPath(data_path)
        obj = self.objects[path]
        if param_name is None:
            return Resolved(obj, None, tuple(instances))
        if pending:
            # Parameters belong to an instance, not to the table itself.
            raise UnknownPath(data_path)
        try:
            return Resolved(obj, obj.parameters[param_name], tuple(instances))
        except KeyError:
            raise UnknownPath(data_path) from None

    def schema_path(self, data_path: str) -> str:
        return self.resolve(data_path).schema_path

    @staticmethod
    def data_path(schema_path: str, *instances: int) -> str:
        """A schema path with its ``{i}`` placeholders filled in order."""
        parts = schema_path.split("{i}")
        if len(parts) - 1 != len(instances):
            raise ValueError(
                f"{schema_path!r} has {len(parts) - 1} instance placeholders, "
                f"{len(instances)} numbers given"
            )
        out = parts[0]
        for number, part in zip(instances, parts[1:], strict=True):
            out += str(number) + part
        return out
