"""The parser against the documents the Forum actually publishes.

These run when the core documents are in the cache (``bbfmodels fetch``
puts them there; CI does that before testing) and are skipped otherwise,
so a contributor without network access can still run the suite.
"""

from __future__ import annotations

import pytest

from bbfmodels import sources
from bbfmodels.ir import Document, Object
from bbfmodels.parser import parse_file

# Lower bounds that catch a parser silently dropping half a document.
EXPECTED = {
    "tr-098-1-8-0-full.xml": ("InternetGatewayDevice", 180, 1500),
    "tr-181-2-21-0-cwmp-full.xml": ("Device", 950, 7000),
    "tr-181-2-21-0-usp-full.xml": ("Device", 1000, 7500),
}


def _cached(name: str) -> str:
    path = sources.cache_dir() / name
    if not path.exists():
        pytest.skip(f"{name} is not in the cache; run 'bbfmodels fetch'")
    return str(path)


@pytest.fixture(scope="module", params=sources.CORE)
def document(request: pytest.FixtureRequest) -> tuple[str, Document]:
    name: str = request.param
    return name, parse_file(_cached(name))


def _objects(doc: Document) -> list[Object]:
    out: list[Object] = []

    def walk(obj: Object) -> None:
        out.append(obj)
        for cmd in obj.commands.values():
            for child in (*cmd.input.objects.values(), *cmd.output.objects.values()):
                walk(child)
        for ev in obj.events.values():
            for child in ev.arguments.objects.values():
                walk(child)

    for model in doc.models:
        for obj in model.objects.values():
            walk(obj)
    return out


def test_parses_and_round_trips(document: tuple[str, Document]) -> None:
    name, doc = document
    assert doc.spec.startswith("urn:broadband-forum-org:")
    assert doc.models
    objects = _objects(doc)
    params = sum(len(o.parameters) for o in objects)
    if name in EXPECTED:
        root, min_objects, min_params = EXPECTED[name]
        assert doc.models[0].root == root
        assert len(objects) >= min_objects
        assert params >= min_params
    # Every multi-instance object states its arity the way the schema requires.
    for obj in objects:
        if obj.multi_instance:
            assert obj.max_entries is None or obj.max_entries > 1 or obj.min_entries == 0, obj.path
    assert Document.model_validate_json(doc.model_dump_json(exclude_defaults=True)) == doc


def test_usp_documents_carry_commands_and_events() -> None:
    doc = parse_file(_cached("tr-181-2-21-0-usp-full.xml"))
    root = doc.models[0].objects["Device."]
    assert doc.protocol == "usp"
    assert "Reboot()" in root.commands
    assert "Boot!" in root.events
    trace = doc.models[0].objects["Device.IP.Diagnostics."].commands["TraceRoute()"]
    assert trace.is_async
    assert "RouteHops.{i}." in trace.output.objects


def test_cwmp_tr181_well_known_facts() -> None:
    doc = parse_file(_cached("tr-181-2-21-0-cwmp-full.xml"))
    assert doc.protocol == "cwmp"
    objects = doc.models[0].objects
    radio = objects["Device.WiFi.Radio.{i}."]
    assert radio.num_entries_parameter == "RadioNumberOfEntries"
    assert radio.max_entries is None
    assert any(k.parameters == ("Alias",) for k in radio.unique_keys)
    channel = radio.parameters["Channel"].syntax
    assert channel.base_type.value == "unsignedInt"
    assert channel.facets.ranges[0].min_inclusive == 1
    bands = radio.parameters["SupportedFrequencyBands"].syntax
    assert bands.list is not None
    assert {e.value for e in bands.facets.enumerations} >= {"2.4GHz", "5GHz"}
    operating = radio.parameters["OperatingFrequencyBand"].syntax.facets.enumeration_ref
    assert operating is not None and operating.target_param == "SupportedFrequencyBands"
    ip = objects["Device.IP.Interface.{i}.IPv4Address.{i}."].parameters["IPAddress"].syntax
    assert ip.data_type == "IPv4Address" and ip.base_type.value == "string"
    lower = objects["Device.IP.Interface.{i}."].parameters["LowerLayers"].syntax
    assert lower.list is not None
    assert lower.facets.path_ref is not None and lower.facets.path_ref.target_type == "row"
