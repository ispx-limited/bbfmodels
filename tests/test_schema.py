from pathlib import Path

import pytest

from bbfmodels import sources
from bbfmodels.parser import parse_file
from bbfmodels.schema import Schema, UnknownPath

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def schema() -> Schema:
    return Schema.from_documents(parse_file(FIXTURES / "mini-cwmp-full.xml"))


def test_lookup(schema: Schema) -> None:
    assert [o.path for o in schema.roots] == ["Device."]
    assert schema.object("Device.Radio.{i}.").num_entries_parameter == "RadioNumberOfEntries"
    assert schema.parameter("Device.Radio.{i}.Channel").syntax.facets.units == "channel"
    assert [o.path for o in schema.children("Device.")] == [
        "Device.Radio.{i}.",
        "Device.Config.{i}.",
    ]
    with pytest.raises(UnknownPath):
        schema.object("Device.Nope.")
    with pytest.raises(UnknownPath):
        schema.parameter("Device.Radio.{i}.Nope")


def test_resolve_data_paths(schema: Schema) -> None:
    r = schema.resolve("Device.Radio.3.Channel")
    assert r.object.path == "Device.Radio.{i}." and r.instances == (3,)
    assert r.parameter is not None and r.parameter.name == "Channel"
    assert r.schema_path == "Device.Radio.{i}.Channel"
    obj = schema.resolve("Device.Radio.3.")
    assert obj.parameter is None and obj.object.path == "Device.Radio.{i}."
    assert schema.resolve("Device.").object.path == "Device."
    assert schema.schema_path("Device.RadioNumberOfEntries") == "Device.RadioNumberOfEntries"
    for bad in ("Device.Radio.Channel", "Device.Radio.1.Nope", "Device.1.", "Other."):
        with pytest.raises(UnknownPath):
            schema.resolve(bad)


def test_data_path_builder() -> None:
    assert Schema.data_path("Device.Radio.{i}.Channel", 2) == "Device.Radio.2.Channel"
    assert Schema.data_path("Device.A.{i}.B.{i}.", 1, 7) == "Device.A.1.B.7."
    with pytest.raises(ValueError):
        Schema.data_path("Device.Radio.{i}.Channel")


def _cached(name: str) -> Path:
    path = sources.cache_dir() / name
    if not path.exists():
        pytest.skip(f"{name} is not in the cache; run 'bbfmodels fetch'")
    return path


def test_service_model_mounts_under_services() -> None:
    schema = Schema.from_documents(
        parse_file(_cached("tr-181-2-21-0-cwmp-full.xml")),
        parse_file(_cached("tr-104-2-0-2-cwmp-full.xml")),
    )
    voice = schema.object("Device.Services.VoiceService.{i}.")
    assert voice.multi_instance
    caps = schema.object("Device.Services.VoiceService.{i}.Capabilities.")
    first = next(iter(caps.parameters))
    r = schema.resolve(f"Device.Services.VoiceService.1.Capabilities.{first}")
    assert r.instances == (1,) and r.parameter is not None and r.parameter.name == first
    assert "IPAddress" in schema.data_types and "DiagnosticsState" in schema.data_types
    radio = schema.resolve("Device.WiFi.Radio.2.Channel")
    assert radio.schema_path == "Device.WiFi.Radio.{i}.Channel"
    with pytest.raises(UnknownPath):
        schema.resolve("Device.WiFi.Radio.2.X_VENDOR_Thing")


def test_service_model_without_a_root_needs_a_mount() -> None:
    voice = parse_file(_cached("tr-104-2-0-2-cwmp-full.xml"))
    with pytest.raises(ValueError):
        Schema.from_documents(voice)
    schema = Schema()
    schema.add(voice, mount="Device.Services.")
    assert "Device.Services.VoiceService.{i}." in schema.objects
