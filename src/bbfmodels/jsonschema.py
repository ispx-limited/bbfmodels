"""JSON Schema for a device's data, emitted from the IR.

The schema describes a device as nested JSON: an object per data model
object, a property per parameter, and a table as an object keyed by
instance number. Every object becomes a definition under ``$defs`` named
like the generated Python class (``WiFi_Radio``), so a consumer in any
language can reference one object's shape. Command inputs and outputs and
event payloads are definitions too, marked with ``x-bbf-command`` or
``x-bbf-event``.

Everything is optional and additional properties are allowed, as in the
generated models: no device exposes the whole model, and vendor
parameters are data, not errors. The Forum's facets are emitted as
constraints (ranges, sizes, patterns, enumerations, list bounds) because a
schema consumer asks for them; ``lenient=True`` leaves them out for a
consumer validating what real devices return. Forum metadata the schema
has no keyword for travels in ``x-bbf-*`` members.
"""

from __future__ import annotations

from typing import Any

from bbfmodels.generate import class_name
from bbfmodels.ir import Arguments, BaseType, Document, Model, Object, Parameter, Syntax
from bbfmodels.paths import member_name

DRAFT = "https://json-schema.org/draft/2020-12/schema"
INSTANCE_KEY = "^[1-9][0-9]*$"

_INT_BOUNDS = {
    BaseType.INT: (-(2**31), 2**31 - 1),
    BaseType.UNSIGNED_INT: (0, 2**32 - 1),
    BaseType.LONG: (-(2**63), 2**63 - 1),
    BaseType.UNSIGNED_LONG: (0, 2**64 - 1),
}


def document_schema(
    doc: Document, *, lenient: bool = False, descriptions: bool = True
) -> dict[str, Any]:
    """The JSON Schema of a document's one model."""
    if len(doc.models) != 1:
        raise ValueError(
            f"{doc.file or doc.spec} has {len(doc.models)} models; one schema per model"
        )
    model = doc.models[0]
    root_obj = next(iter(model.objects.values()))
    root = root_obj.name
    emitter = _Emitter(model, root, lenient, descriptions)
    defs: dict[str, Any] = {}
    for obj in model.objects.values():
        defs[class_name(obj, root)] = emitter.object(obj, obj.path)
        emitter.arguments(obj, root, defs)
    root_name = class_name(root_obj, root)
    schema: dict[str, Any] = {
        "$schema": DRAFT,
        "$id": f"urn:bbfmodels:{doc.spec}",
        "title": model.name,
        "x-bbf-spec": doc.spec,
        "x-bbf-source": doc.file,
    }
    if descriptions and doc.description:
        schema["description"] = doc.description
    if root_obj.multi_instance:
        schema.update(_table_ref(root_name))
        schema["x-bbf-path"] = root_obj.path
    else:
        schema["$ref"] = f"#/$defs/{root_name}"
    schema["$defs"] = defs
    return schema


def _table_ref(name: str) -> dict[str, Any]:
    return {
        "type": "object",
        "patternProperties": {INSTANCE_KEY: {"$ref": f"#/$defs/{name}"}},
        "additionalProperties": False,
    }


class _Emitter:
    def __init__(self, model: Model, root: str, lenient: bool, descriptions: bool) -> None:
        self.model = model
        self.root = root
        self.lenient = lenient
        self.descriptions = descriptions

    def object(
        self, obj: Object, path: str, children: list[tuple[str, str, bool]] | None = None
    ) -> dict[str, Any]:
        """One object's schema. ``children`` overrides the model lookup for argument objects."""
        props: dict[str, Any] = {}
        for param in obj.parameters.values():
            props[param.name] = self.parameter(param)
        if children is None:
            children = [
                (c.name, class_name(c, self.root), c.multi_instance)
                for c in self.model.objects.values()
                if c.parent_path == path
            ]
        for name, def_name, multi in children:
            props[name] = _table_ref(def_name) if multi else {"$ref": f"#/$defs/{def_name}"}
        out: dict[str, Any] = {"type": "object", "x-bbf-path": path}
        if obj.access is not None:
            out["x-bbf-access"] = obj.access.value
        if obj.multi_instance:
            out["x-bbf-table"] = {
                "minEntries": obj.min_entries,
                "maxEntries": obj.max_entries,
                "numEntriesParameter": obj.num_entries_parameter,
                "uniqueKeys": [list(k.parameters) for k in obj.unique_keys],
            }
        if obj.status.value != "current":
            out["x-bbf-status"] = obj.status.value
        if self.descriptions and obj.description:
            out["description"] = obj.description
        out["properties"] = props
        out["additionalProperties"] = True
        return out

    def parameter(self, param: Parameter) -> dict[str, Any]:
        out = self.syntax(param.syntax)
        if param.access is not None:
            out["x-bbf-access"] = param.access.value
        if param.status.value != "current":
            out["x-bbf-status"] = param.status.value
        if param.version:
            out["x-bbf-version"] = param.version
        if param.mandatory is not None:
            out["x-bbf-mandatory"] = param.mandatory
        if self.descriptions and param.description:
            out["description"] = param.description
        return out

    def syntax(self, s: Syntax) -> dict[str, Any]:
        item = self._scalar(s)
        if s.data_type:
            item["x-bbf-datatype"] = s.data_type
        if s.facets.units:
            item["x-bbf-units"] = s.facets.units
        if s.list is None:
            return item
        out: dict[str, Any] = {"type": "array", "items": item, "x-bbf-list": True}
        if not self.lenient:
            if s.list.min_items is not None:
                out["minItems"] = s.list.min_items
            if s.list.max_items is not None:
                out["maxItems"] = s.list.max_items
        return out

    def _scalar(self, s: Syntax) -> dict[str, Any]:
        f = s.facets
        match s.base_type:
            case BaseType.STRING:
                out: dict[str, Any] = {"type": "string"}
                if not self.lenient:
                    if len(f.sizes) == 1:
                        if f.sizes[0].min_length is not None:
                            out["minLength"] = f.sizes[0].min_length
                        if f.sizes[0].max_length is not None:
                            out["maxLength"] = f.sizes[0].max_length
                    if f.enumerations and f.enumeration_ref is None:
                        out["enum"] = [e.value for e in f.enumerations]
                    patterns = [p.value for p in f.patterns if p.value]
                    if len(patterns) == 1:
                        out["pattern"] = f"^(?:{patterns[0]})$"
                    elif len(patterns) > 1:
                        out["anyOf"] = [{"pattern": f"^(?:{p})$"} for p in patterns]
                if f.enumerations and (self.lenient or f.enumeration_ref is not None):
                    out["x-bbf-enum"] = [e.value for e in f.enumerations]
                if f.enumeration_ref is not None:
                    out["x-bbf-enumerationRef"] = f.enumeration_ref.target_param
                if f.path_ref is not None:
                    out["x-bbf-pathRef"] = {
                        "refType": f.path_ref.ref_type,
                        "targetParent": f.path_ref.target_parent,
                        "targetType": f.path_ref.target_type,
                    }
                return out
            case BaseType.INT | BaseType.UNSIGNED_INT | BaseType.LONG | BaseType.UNSIGNED_LONG:
                low, high = _INT_BOUNDS[s.base_type]
                out = {"type": "integer"}
                if not self.lenient:
                    if f.ranges:
                        out["minimum"] = min(
                            (r.min_inclusive for r in f.ranges if r.min_inclusive is not None),
                            default=low,
                        )
                        out["maximum"] = max(
                            (r.max_inclusive for r in f.ranges if r.max_inclusive is not None),
                            default=high,
                        )
                    else:
                        out["minimum"], out["maximum"] = low, high
                return out
            case BaseType.BOOLEAN:
                return {"type": "boolean"}
            case BaseType.DATE_TIME:
                return {"type": "string", "format": "date-time"}
            case BaseType.HEX_BINARY:
                out = {"type": "string", "pattern": "^([0-9A-Fa-f]{2})*$"}
                if not self.lenient and len(f.sizes) == 1 and f.sizes[0].max_length is not None:
                    out["maxLength"] = f.sizes[0].max_length * 2
                return out
            case BaseType.BASE64:
                return {"type": "string", "contentEncoding": "base64"}
            case BaseType.DECIMAL:
                return {"type": "number"}
        raise ValueError(f"unknown base type {s.base_type!r}")

    def arguments(self, obj: Object, root: str, defs: dict[str, Any]) -> None:
        owner = class_name(obj, root)
        for cmd in obj.commands.values():
            base = f"{owner}_{member_name(cmd.name)}"
            path = f"{obj.path}{cmd.name}"
            for side, args in (("Input", cmd.input), ("Output", cmd.output)):
                name = f"{base}_{side}"
                self._argument_defs(name, f"{path}.{side}.", args, defs)
                defs[name]["x-bbf-command"] = {
                    "path": path,
                    "side": side.lower(),
                    "async": cmd.is_async,
                }
        for ev in obj.events.values():
            name = f"{owner}_{member_name(ev.name)}_Event"
            self._argument_defs(name, f"{obj.path}{ev.name}.", ev.arguments, defs)
            defs[name]["x-bbf-event"] = f"{obj.path}{ev.name}"

    def _argument_defs(self, name: str, path: str, args: Arguments, defs: dict[str, Any]) -> None:
        def children_of(rel: str) -> list[tuple[str, str, bool]]:
            out = []
            for child_rel in args.objects:
                parent = child_rel[:-4] if child_rel.endswith("{i}.") else child_rel
                parent = parent.rstrip(".").rpartition(".")[0]
                parent = parent + "." if parent else ""
                if parent == rel:
                    segments = [s for s in child_rel.rstrip(".").split(".") if s != "{i}"]
                    out.append(
                        (segments[-1], f"{name}_{'_'.join(segments)}", child_rel.endswith("{i}."))
                    )
            return out

        for rel, nested in args.objects.items():
            segments = [s for s in rel.rstrip(".").split(".") if s != "{i}"]
            defs[f"{name}_{'_'.join(segments)}"] = self.object(nested, path + rel, children_of(rel))
        holder = Object(path=path, parameters=args.parameters)
        defs[name] = self.object(holder, path, children_of(""))
