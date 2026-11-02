from pathlib import Path

import pytest

from bbfmodels import codec
from bbfmodels.parser import parse_file
from bbfmodels.schema import Schema
from bbfmodels.tree import Node, Table, Tree

FIXTURES = Path(__file__).parent / "fixtures"

FLAT = {
    "Device.RadioNumberOfEntries": "2",
    "Device.Radio.1.Enable": "1",
    "Device.Radio.1.Channel": "36",
    "Device.Radio.1.Standards": "a, b",
    "Device.Radio.2.Enable": "false",
    "Device.Radio.2.Band": "5GHz",
    "Device.Radio.2.X_EXAMPLE_Power": "high",
    "Device.X_EXAMPLE_Thing.1.Foo": "bar",
    "Device.X_EXAMPLE_Thing.2.Foo": "baz",
    "Device.X_EXAMPLE_Single.Baz": "1",
}


@pytest.fixture(scope="module")
def schema() -> Schema:
    return Schema.from_documents(parse_file(FIXTURES / "mini-cwmp-full.xml"))


@pytest.fixture
def tree(schema: Schema) -> Tree:
    return Tree.from_flat(schema, FLAT)


def test_round_trip_is_exact(tree: Tree) -> None:
    assert tree.flatten() == FLAT
    assert list(tree.flatten()) == list(FLAT)


def test_structure(tree: Tree) -> None:
    device = tree["Device"]
    assert isinstance(device, Node) and device.object is not None
    radios = device["Radio"]
    assert isinstance(radios, Table) and sorted(radios) == [1, 2]
    assert radios[1].path == "Device.Radio.1." and radios[1].object is not None
    assert radios[1].object.path == "Device.Radio.{i}."
    thing = device["X_EXAMPLE_Thing"]
    assert isinstance(thing, Table) and thing.object is None and sorted(thing) == [1, 2]
    single = device["X_EXAMPLE_Single"]
    assert isinstance(single, Node) and single.object is None
    assert "Baz" in single and single.unknown_parameters == ["Baz"]
    assert radios[2].unknown_parameters == ["X_EXAMPLE_Power"]
    assert [n.path for n in tree.nodes()] == [
        "Device.",
        "Device.Radio.1.",
        "Device.Radio.2.",
        "Device.X_EXAMPLE_Thing.1.",
        "Device.X_EXAMPLE_Thing.2.",
        "Device.X_EXAMPLE_Single.",
    ]
    assert list(device.children) == ["X_EXAMPLE_Single"]
    assert list(device.tables) == ["Radio", "X_EXAMPLE_Thing"]


def test_values_decode_on_demand(tree: Tree) -> None:
    assert tree.value("Device.RadioNumberOfEntries") == 2
    assert tree.value("Device.Radio.1.Enable") is True
    assert tree.value("Device.Radio.2.Enable") is False
    assert tree.value("Device.Radio.1.Standards") == ["a", "b"]
    assert tree.text("Device.Radio.1.Standards") == "a, b"
    assert tree.value("Device.Radio.2.X_EXAMPLE_Power") == "high"
    assert tree.value("Device.X_EXAMPLE_Thing.1.Foo") == "bar"
    radios = tree["Device"]["Radio"]
    assert isinstance(radios, Table)
    assert radios[1].get("Channel") == 36 and radios[1].get("Band", "none") == "none"


def test_set_encodes(tree: Tree) -> None:
    tree.set("Device.Radio.1.Enable", False)
    tree.set("Device.Radio.1.Standards", ["b"])
    tree.set("Device.Radio.3.Channel", 11)
    tree.set("Device.Radio.3.X_EXAMPLE_Power", "low")
    flat = tree.flatten()
    assert flat["Device.Radio.1.Enable"] == "false"
    assert flat["Device.Radio.1.Standards"] == "b"
    assert flat["Device.Radio.3.Channel"] == "11"
    assert flat["Device.Radio.3.X_EXAMPLE_Power"] == "low"
    with pytest.raises(codec.CodecError):
        tree.set("Device.Radio.1.Channel", "11")
    with pytest.raises(codec.CodecError):
        tree.set("Device.Radio.1.X_EXAMPLE_Power", 1)


def test_problems(tree: Tree) -> None:
    assert tree.problems() == []
    tree.set_text("Device.Radio.1.Channel", "999")
    tree.set_text("Device.Radio.2.Band", "7GHz")
    tree.set_text("Device.Radio.2.X_EXAMPLE_Power", "whatever")
    assert tree.problems() == [
        ("Device.Radio.1.Channel", "999 is outside the allowed ranges"),
        ("Device.Radio.2.Band", "'7GHz' is not one of the enumerated values"),
    ]


def test_missing_paths_raise(tree: Tree) -> None:
    with pytest.raises(KeyError):
        tree.node("Device.Radio.9.")
    with pytest.raises(KeyError):
        tree.text("Device.Radio.1.Band")
    with pytest.raises(KeyError):
        tree["Other"]
