"""JSON Schema emitted from the IR, checked against real model output."""

from __future__ import annotations

from pathlib import Path

import jsonschema
import pytest

from bbfmodels import sources
from bbfmodels.jsonschema import document_schema
from bbfmodels.parser import parse_file

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def schema() -> dict:  # type: ignore[type-arg]
    return document_schema(parse_file(FIXTURES / "mini-cwmp-full.xml"))


def test_shape(schema: dict) -> None:  # type: ignore[type-arg]
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["$ref"] == "#/$defs/Device" and schema["title"] == "Device_vendor-1.2:2.0"
    device = schema["$defs"]["Device"]
    assert device["x-bbf-path"] == "Device." and device["additionalProperties"] is True
    assert "required" not in device
    assert device["properties"]["Radio"]["patternProperties"]["^[1-9][0-9]*$"] == {
        "$ref": "#/$defs/Radio"
    }
    radio = schema["$defs"]["Radio"]
    assert radio["x-bbf-table"]["numEntriesParameter"] == "RadioNumberOfEntries"
    assert radio["x-bbf-table"]["uniqueKeys"] == [["Alias"], ["Name", "Channel"]]
    p = radio["properties"]
    assert p["Channel"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 255,
        "x-bbf-units": "channel",
        "x-bbf-access": "readWrite",
    }
    assert p["Band"]["enum"] == ["2.4GHz", "5GHz", "6GHz"]
    assert p["Standards"]["type"] == "array" and p["Standards"]["maxItems"] == 3
    assert p["Standards"]["items"]["enum"] == ["a", "b"]
    assert p["BytesSent"]["x-bbf-datatype"] == "StatsCounter32" and p["BytesSent"]["minimum"] == 0
    assert p["Address"]["x-bbf-datatype"] == "IPv4Address" and p["Address"]["maxLength"] == 15
    assert p["Address"]["pattern"] == "^(?:[0-9.]+)$"
    assert p["Mode"]["x-bbf-enumerationRef"] == "#.ModesSupported" and "enum" not in p["Mode"]
    assert p["LowerLayer"]["x-bbf-pathRef"]["targetParent"] == "Device.Radio."
    assert schema["$defs"]["Device"]["properties"]["Reset"]["x-bbf-status"] == "deprecated"
    assert schema["$defs"]["Device"]["properties"]["Password"]["maxLength"] == 64
    assert "description" in radio


def test_lenient_and_without_descriptions() -> None:
    doc = parse_file(FIXTURES / "mini-cwmp-full.xml")
    lenient = document_schema(doc, lenient=True, descriptions=False)
    radio = lenient["$defs"]["Radio"]["properties"]
    assert radio["Channel"] == {
        "type": "integer",
        "x-bbf-units": "channel",
        "x-bbf-access": "readWrite",
    }
    assert "enum" not in radio["Band"] and radio["Band"]["x-bbf-enum"] == ["2.4GHz", "5GHz", "6GHz"]
    assert "description" not in lenient["$defs"]["Radio"]


def test_validates_instances(schema: dict) -> None:  # type: ignore[type-arg]
    validator = jsonschema.Draft202012Validator(schema)
    good = {
        "RadioNumberOfEntries": 1,
        "Radio": {"1": {"Enable": True, "Channel": 36, "Band": "5GHz", "Standards": ["a"]}},
        "X_EXAMPLE_Thing": {"1": {"Foo": "bar"}},
    }
    assert list(validator.iter_errors(good)) == []
    bad = {"Radio": {"1": {"Channel": 999, "Band": "7GHz"}, "x": {}}}
    messages = sorted(e.message for e in validator.iter_errors(bad))
    assert messages == [
        "'7GHz' is not one of ['2.4GHz', '5GHz', '6GHz']",
        "'x' does not match any of the regexes: '^[1-9][0-9]*$'",
        "999 is greater than the maximum of 255",
    ]


def test_usp_commands_and_events_are_definitions() -> None:
    schema = document_schema(parse_file(FIXTURES / "mini-usp-full.xml"))
    out = schema["$defs"]["Device_TraceRoute_Output"]
    assert out["x-bbf-command"] == {"path": "Device.TraceRoute()", "side": "output", "async": True}
    assert out["properties"]["RouteHops"]["patternProperties"]["^[1-9][0-9]*$"] == {
        "$ref": "#/$defs/Device_TraceRoute_Output_RouteHops"
    }
    assert (
        schema["$defs"]["Device_TraceRoute_Input"]["properties"]["Host"]["x-bbf-mandatory"] is True
    )
    assert schema["$defs"]["Device_Boot_Event"]["x-bbf-event"] == "Device.Boot!"
    jsonschema.Draft202012Validator.check_schema(schema)


def test_service_model_root_is_a_table() -> None:
    schema = document_schema(parse_file(FIXTURES / "mini-service-full.xml"))
    assert schema["patternProperties"]["^[1-9][0-9]*$"] == {"$ref": "#/$defs/VoiceService"}
    assert schema["x-bbf-path"] == "VoiceService.{i}."


def _cached(name: str) -> Path:
    path = sources.cache_dir() / name
    if not path.exists():
        pytest.skip(f"{name} is not in the cache; run 'bbfmodels fetch'")
    return path


def test_tr181_model_output_validates() -> None:
    from bbfmodels.tr181_cwmp import Device

    schema = document_schema(parse_file(_cached("tr-181-2-21-0-cwmp-full.xml")))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    device = Device.from_flat(
        {
            "Device.DeviceInfo.UpTime": "1234",
            "Device.DeviceInfo.FirstUseDate": "2026-01-02T03:04:05Z",
            "Device.WiFi.Radio.1.Enable": "1",
            "Device.WiFi.Radio.1.Channel": "36",
            "Device.WiFi.Radio.1.SupportedFrequencyBands": "2.4GHz,5GHz",
            "Device.WiFi.Radio.1.X_EXAMPLE_TxPower": "high",
            "Device.FAP.PerfMgmt.Config.1.URL": "https://example.net/pm",
        }
    )
    data = device.model_dump(mode="json", by_alias=True, exclude_none=True, exclude_defaults=True)
    assert data["FAP"]["PerfMgmt"]["Config"]["1"]["URL"].startswith("https")
    assert list(validator.iter_errors(data)) == []
    device.WiFi.Radio[1].Channel = 999  # type: ignore[union-attr]
    data = device.model_dump(mode="json", by_alias=True, exclude_none=True, exclude_defaults=True)
    assert [e.message for e in validator.iter_errors(data)] == [
        "999 is greater than the maximum of 255"
    ]
