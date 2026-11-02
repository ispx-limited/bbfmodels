"""The intermediate representation (IR) of a Broadband Forum data model.

The IR is the contract between the parser and everything else. The parser
turns a published TR-106 XML document into one ``Document``; the runtime
and every code generator read the ``Document`` and never the XML. It is a
plain, fully resolved description of the model:

- Every object carries its parameters, and for USP its commands and events,
  keyed by name in document order.
- Every parameter's syntax carries its effective base type and facets, with
  named data types (``IPAddress``, ``StatsCounter32``) already resolved
  through their inheritance chain, so a consumer needs no second lookup.
  The name of the data type is kept as well, for emitters that want to
  generate one named type and refer to it.
- Paths keep the Forum's spelling. A multi-instance object's path ends in
  ``{i}.`` exactly as the specification writes it; a data path on a device
  replaces ``{i}`` with an instance number.
- An attribute the document leaves out is ``None`` or the schema's default
  (an object or parameter without ``status`` is current).

The models are pydantic so the IR serialises to JSON and has a JSON Schema
of its own without a second description of it.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Status(StrEnum):
    CURRENT = "current"
    DEPRECATED = "deprecated"
    OBSOLETED = "obsoleted"
    DELETED = "deleted"


class Access(StrEnum):
    READ_ONLY = "readOnly"
    READ_WRITE = "readWrite"
    WRITE_ONCE_READ_ONLY = "writeOnceReadOnly"


class BaseType(StrEnum):
    """The primitive types of TR-106. Every parameter resolves to one."""

    STRING = "string"
    INT = "int"
    UNSIGNED_INT = "unsignedInt"
    LONG = "long"
    UNSIGNED_LONG = "unsignedLong"
    BOOLEAN = "boolean"
    DATE_TIME = "dateTime"
    HEX_BINARY = "hexBinary"
    BASE64 = "base64"
    DECIMAL = "decimal"


class ActiveNotify(StrEnum):
    NORMAL = "normal"
    FORCE_ENABLED = "forceEnabled"
    FORCE_DEFAULT_ENABLED = "forceDefaultEnabled"
    CAN_DENY = "canDeny"


class _Node(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Size(_Node):
    min_length: int | None = None
    max_length: int | None = None


class Range(_Node):
    min_inclusive: int | None = None
    max_inclusive: int | None = None
    step: int | None = None


class Enumeration(_Node):
    value: str
    code: int | None = None
    access: Access | None = None
    optional: bool = False
    status: Status = Status.CURRENT
    version: str | None = None
    description: str = ""


class Pattern(_Node):
    value: str
    status: Status = Status.CURRENT
    version: str | None = None
    description: str = ""


class PathRef(_Node):
    """The parameter holds the path of another object or parameter."""

    ref_type: Literal["strong", "weak"] = "strong"
    target_parent: str | None = None
    target_type: str = "row"
    target_data_type: str | None = None


class InstanceRef(_Node):
    """The parameter holds the instance number of a row of another table."""

    ref_type: Literal["strong", "weak"] = "strong"
    target_parent: str | None = None


class EnumerationRef(_Node):
    """The allowed values are whatever another parameter lists."""

    target_param: str
    null_value: str | None = None


class Facets(_Node):
    """Constraints on a value. Which ones apply depends on the base type."""

    sizes: tuple[Size, ...] = ()
    ranges: tuple[Range, ...] = ()
    enumerations: tuple[Enumeration, ...] = ()
    patterns: tuple[Pattern, ...] = ()
    units: str | None = None
    path_ref: PathRef | None = None
    instance_ref: InstanceRef | None = None
    enumeration_ref: EnumerationRef | None = None

    def merged_over(self, base: Facets) -> Facets:
        """These facets applied on top of an inherited set.

        A facet kind stated here replaces the inherited one of the same kind;
        a kind left unstated is inherited. This is how a parameter that uses
        a named data type narrows it, for example a ``StatsCounter64`` with
        its own units.
        """
        return Facets(
            sizes=self.sizes or base.sizes,
            ranges=self.ranges or base.ranges,
            enumerations=self.enumerations or base.enumerations,
            patterns=self.patterns or base.patterns,
            units=self.units if self.units is not None else base.units,
            path_ref=self.path_ref or base.path_ref,
            instance_ref=self.instance_ref or base.instance_ref,
            enumeration_ref=self.enumeration_ref or base.enumeration_ref,
        )


class ListFacets(_Node):
    """The parameter is a comma-separated list of items of the base type."""

    min_items: int | None = None
    max_items: int | None = None
    sizes: tuple[Size, ...] = ()
    nested_brackets: bool = False


class DataType(_Node):
    """A named data type defined at document level."""

    name: str
    base: str | None = None
    base_type: BaseType
    facets: Facets = Facets()
    list: ListFacets | None = None
    description: str = ""
    status: Status = Status.CURRENT


class Default(_Node):
    kind: Literal["object", "factory", "implementation", "parameter"]
    value: str
    status: Status = Status.CURRENT


class Syntax(_Node):
    base_type: BaseType
    data_type: str | None = None
    facets: Facets = Facets()
    list: ListFacets | None = None
    hidden: bool = False
    secured: bool = False
    command: bool = False
    default: Default | None = None


class Parameter(_Node):
    name: str
    access: Access | None = None
    description: str = ""
    version: str | None = None
    status: Status = Status.CURRENT
    active_notify: ActiveNotify = ActiveNotify.NORMAL
    forced_inform: bool = False
    mandatory: bool | None = None
    syntax: Syntax


class UniqueKey(_Node):
    functional: bool = True
    parameters: tuple[str, ...]


class Arguments(_Node):
    """The input or output of a command, or the payload of an event."""

    parameters: dict[str, Parameter] = Field(default_factory=dict)
    objects: dict[str, Object] = Field(default_factory=dict)


class Command(_Node):
    name: str
    is_async: bool = False
    description: str = ""
    version: str | None = None
    status: Status = Status.CURRENT
    input: Arguments = Field(default_factory=Arguments)
    output: Arguments = Field(default_factory=Arguments)


class Event(_Node):
    name: str
    description: str = ""
    version: str | None = None
    status: Status = Status.CURRENT
    arguments: Arguments = Field(default_factory=Arguments)


class Object(_Node):
    """An object of the model, keyed by its path.

    ``path`` is the full path with a trailing dot, ``Device.WiFi.Radio.{i}.``.
    Inside a command's arguments or an event's payload it is relative to the
    containing object, ``RouteHops.{i}.``.
    """

    path: str
    access: Access | None = None
    min_entries: int = 1
    max_entries: int | None = 1
    num_entries_parameter: str | None = None
    enable_parameter: str | None = None
    discriminator_parameter: str | None = None
    mount_type: str | None = None
    unique_keys: tuple[UniqueKey, ...] = ()
    description: str = ""
    version: str | None = None
    status: Status = Status.CURRENT
    parameters: dict[str, Parameter] = Field(default_factory=dict)
    commands: dict[str, Command] = Field(default_factory=dict)
    events: dict[str, Event] = Field(default_factory=dict)

    @property
    def name(self) -> str:
        """The last segment of the path, ``Radio`` for ``Device.WiFi.Radio.{i}.``."""
        parts = self.path.rstrip(".").split(".")
        return parts[-2] if parts[-1] == "{i}" else parts[-1]

    @property
    def multi_instance(self) -> bool:
        return self.path.endswith("{i}.")

    @property
    def parent_path(self) -> str:
        """The containing object's path, or ``""`` for a root object."""
        stem = self.path[:-4] if self.multi_instance else self.path
        head = stem.rstrip(".").rpartition(".")[0]
        return head + "." if head else ""


# Arguments refers to Object, which is defined after it.
Arguments.model_rebuild()


class ProfileObject(_Node):
    path: str
    requirement: str
    parameters: dict[str, str] = Field(default_factory=dict)
    commands: dict[str, str] = Field(default_factory=dict)
    events: dict[str, str] = Field(default_factory=dict)


class Profile(_Node):
    name: str
    base: str | None = None
    extends: tuple[str, ...] = ()
    version: str | None = None
    status: Status = Status.CURRENT
    description: str = ""
    parameters: dict[str, str] = Field(default_factory=dict)
    objects: dict[str, ProfileObject] = Field(default_factory=dict)


class Model(_Node):
    """A root data model, ``Device:2.21``, or a service model, ``VoiceService:2.0``."""

    name: str
    is_service: bool = False
    description: str = ""
    parameters: dict[str, Parameter] = Field(default_factory=dict)
    objects: dict[str, Object] = Field(default_factory=dict)
    profiles: dict[str, Profile] = Field(default_factory=dict)

    @property
    def root(self) -> str:
        return self.name.partition(":")[0]

    @property
    def version(self) -> str:
        return self.name.partition(":")[2]


class Document(_Node):
    """One parsed data model document."""

    spec: str
    file: str | None = None
    protocol: Literal["cwmp", "usp"] | None = None
    description: str = ""
    data_types: dict[str, DataType] = Field(default_factory=dict)
    models: tuple[Model, ...] = ()
