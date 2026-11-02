"""A data tree: the values of one device, held against a schema.

The wire shape of CWMP and USP is a flat list of path and text pairs with
instance numbers inside the paths. ``Tree.from_flat`` arranges those into
objects, tables and instances using the schema, decodes values on demand,
and ``flatten`` writes them back out. Paths the schema does not define are
kept where they belong and come back out unchanged, so a tree built from a
device's values is never lossy.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping

from bbfmodels import codec
from bbfmodels.ir import Object, Parameter
from bbfmodels.schema import Schema, UnknownPath


class Node:
    """One object instance: its parameter texts, child objects and tables."""

    def __init__(self, path: str, obj: Object | None) -> None:
        self.path = path
        self.object = obj
        self.raw: dict[str, str] = {}
        # Child objects and tables by name, in the order they were first seen,
        # so a tree flattens in the order it was built from.
        self.members: dict[str, Node | Table] = {}

    def __repr__(self) -> str:
        return f"Node({self.path!r})"

    def __getitem__(self, name: str) -> Node | Table:
        return self.members[name]

    def __contains__(self, name: str) -> bool:
        return name in self.raw or name in self.members

    @property
    def children(self) -> dict[str, Node]:
        return {n: m for n, m in self.members.items() if isinstance(m, Node)}

    @property
    def tables(self) -> dict[str, Table]:
        return {n: m for n, m in self.members.items() if isinstance(m, Table)}

    def parameter(self, name: str) -> Parameter | None:
        return self.object.parameters.get(name) if self.object else None

    def text(self, name: str) -> str:
        """The wire text of a parameter, exactly as given."""
        return self.raw[name]

    def value(self, name: str) -> codec.Value:
        """The decoded value of a parameter; text when the schema has no syntax for it."""
        text = self.raw[name]
        param = self.parameter(name)
        return codec.decode(param.syntax, text) if param else text

    def get(self, name: str, default: codec.Value | None = None) -> codec.Value | None:
        return self.value(name) if name in self.raw else default

    def set(self, name: str, value: codec.Value) -> None:
        """Store a value, encoding it for the parameter's syntax.

        An unknown parameter takes text only. Values are not validated here;
        ``Tree.problems`` reports violations of the schema's facets.
        """
        param = self.parameter(name)
        if param is None:
            if not isinstance(value, str):
                raise codec.CodecError(f"{self.path}{name} is not in the schema; give text")
            self.raw[name] = value
        else:
            self.raw[name] = codec.encode(param.syntax, value)

    @property
    def unknown_parameters(self) -> list[str]:
        return [n for n in self.raw if self.parameter(n) is None]

    def walk(self) -> Iterator[Node]:
        yield self
        for member in self.members.values():
            if isinstance(member, Node):
                yield from member.walk()
            else:
                for instance in member.values():
                    yield from instance.walk()


class Table(dict[int, Node]):
    """The instances of a multi-instance object, by instance number."""

    def __init__(self, path: str, obj: Object | None) -> None:
        super().__init__()
        self.path = path
        self.object = obj

    def __repr__(self) -> str:
        return f"Table({self.path!r}, {sorted(self)})"


class Tree:
    def __init__(self, schema: Schema) -> None:
        self.schema = schema
        self.roots: dict[str, Node] = {}

    @classmethod
    def from_flat(cls, schema: Schema, values: Mapping[str, str]) -> Tree:
        tree = cls(schema)
        for path, text in values.items():
            tree.set_text(path, text)
        return tree

    def __getitem__(self, root: str) -> Node:
        return self.roots[root.rstrip(".")]

    def node(self, object_path: str, create: bool = False) -> Node:
        """The node for a data path ending in ``.``, created on the way if asked."""
        segments = object_path.rstrip(".").split(".")
        root_name = segments[0]
        if root_name not in self.roots:
            if not create:
                raise KeyError(object_path)
            self.roots[root_name] = Node(root_name + ".", self._object(root_name + "."))
        node = self.roots[root_name]
        path = root_name + "."
        i = 1
        while i < len(segments):
            seg = segments[i]
            table_path = path + seg + ".{i}."
            is_table = (i + 1 < len(segments) and segments[i + 1].isdigit()) and (
                table_path in self.schema.objects or path + seg + "." not in self.schema.objects
            )
            if is_table:
                number = int(segments[i + 1])
                table = node.members.get(seg)
                if not isinstance(table, Table):
                    if table is not None or not create:
                        raise KeyError(object_path)
                    table = node.members[seg] = Table(table_path, self._object(table_path))
                instance_path = f"{path}{seg}.{number}."
                instance = table.get(number)
                if instance is None:
                    if not create:
                        raise KeyError(object_path)
                    instance = table[number] = Node(instance_path, table.object)
                node, path = instance, instance_path
                i += 2
            else:
                child_path = path + seg + "."
                child = node.members.get(seg)
                if not isinstance(child, Node):
                    if child is not None or not create:
                        raise KeyError(object_path)
                    child = node.members[seg] = Node(child_path, self._object(child_path))
                node, path = child, child_path
                i += 1
        return node

    def _object(self, data_path: str) -> Object | None:
        try:
            return self.schema.resolve(data_path).object
        except UnknownPath:
            return None

    def set_text(self, path: str, text: str) -> None:
        object_path, _, name = path.rpartition(".")
        self.node(object_path + ".", create=True).raw[name] = text

    def set(self, path: str, value: codec.Value) -> None:
        object_path, _, name = path.rpartition(".")
        self.node(object_path + ".", create=True).set(name, value)

    def text(self, path: str) -> str:
        object_path, _, name = path.rpartition(".")
        return self.node(object_path + ".").text(name)

    def value(self, path: str) -> codec.Value:
        object_path, _, name = path.rpartition(".")
        return self.node(object_path + ".").value(name)

    def nodes(self) -> Iterator[Node]:
        for root in self.roots.values():
            yield from root.walk()

    def flatten(self) -> dict[str, str]:
        """Every parameter as path and wire text, in tree order."""
        return {node.path + name: text for node in self.nodes() for name, text in node.raw.items()}

    def problems(self) -> list[tuple[str, str]]:
        """Every facet violation in the tree, as path and message."""
        found: list[tuple[str, str]] = []
        for node in self.nodes():
            for name, text in node.raw.items():
                param = node.parameter(name)
                if param is not None:
                    found.extend((node.path + name, p) for p in codec.problems(param.syntax, text))
        return found
