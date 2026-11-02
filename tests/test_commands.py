"""USP commands and events: in the schema, the generated models and the paths."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from bbfmodels import codec, generate
from bbfmodels.ir import BaseType, ListFacets, Syntax
from bbfmodels.parser import parse_file
from bbfmodels.paths import CommandPath, EventPath
from bbfmodels.schema import Schema

FIXTURES = Path(__file__).parent / "fixtures"


def test_schema_indexes_arguments_under_the_command_and_event() -> None:
    schema = Schema.from_documents(parse_file(FIXTURES / "mini-usp-full.xml"))
    assert "Device.TraceRoute().Input." in schema.objects
    assert "Device.TraceRoute().Output." in schema.objects
    assert "Device.TraceRoute().Output.RouteHops.{i}." in schema.objects
    assert "Device.Boot!." in schema.objects
    assert schema.parameter("Device.TraceRoute().Input.Host").mandatory is True
    assert schema.parameter("Device.Boot!.CommandKey").syntax.base_type is BaseType.STRING
    r = schema.resolve("Device.TraceRoute().Output.RouteHops.3.Host")
    assert r.instances == (3,) and r.parameter is not None
    # argument objects are not children of the object that owns the command
    assert [o.path for o in schema.children("Device.")] == ["Device.Services."]


def test_xsd_types() -> None:
    assert codec.xsd_type(Syntax(base_type=BaseType.UNSIGNED_INT)) == "xsd:unsignedInt"
    assert codec.xsd_type(Syntax(base_type=BaseType.BOOLEAN)) == "xsd:boolean"
    assert codec.xsd_type(Syntax(base_type=BaseType.BASE64)) == "xsd:base64Binary"
    assert codec.xsd_type(Syntax(base_type=BaseType.DATE_TIME)) == "xsd:dateTime"
    assert codec.xsd_type(Syntax(base_type=BaseType.INT, list=ListFacets())) == "xsd:string"


@pytest.fixture(scope="module")
def usp(tmp_path_factory: pytest.TempPathFactory) -> object:
    root = tmp_path_factory.mktemp("usp")
    generate.write_package("miniusp.models", FIXTURES / "mini-usp-full.xml", root)
    (root / "miniusp" / "__init__.py").write_text("")
    sys.path.insert(0, str(root))
    try:
        return importlib.import_module("miniusp.models")
    finally:
        sys.path.pop(0)


def test_generated_command_and_event_classes(usp: object) -> None:
    commands = usp.COMMANDS  # type: ignore[attr-defined]
    events = usp.EVENTS  # type: ignore[attr-defined]
    assert set(commands) == {"Device.Reboot()", "Device.TraceRoute()"}
    assert set(events) == {"Device.Boot!"}
    reboot_in, reboot_out = commands["Device.Reboot()"]
    assert (
        reboot_in.__name__ == "Device_Reboot_Input"
        and reboot_out.__name__ == "Device_Reboot_Output"
    )
    assert list(reboot_in.model_fields) == ["Cause"] and reboot_out.model_fields == {}
    trace_in, trace_out = commands["Device.TraceRoute()"]
    assert trace_in.__bbf_path__ == "Device.TraceRoute().Input."
    request = trace_in(Host="example.net")
    assert request.flatten("") == {"Host": "example.net"}
    response = trace_out.from_flat(
        {"ResponseTime": "12", "RouteHops.1.Host": "gw", "RouteHops.2.Host": "core"}
    )
    assert response.ResponseTime == 12
    assert sorted(response.RouteHops) == [1, 2] and response.RouteHops[1].Host == "gw"
    assert response.problems() == []
    response.ResponseTime = -1
    assert response.problems() == [
        ("Device.TraceRoute().Output.ResponseTime", "-1 is outside the unsignedInt range")
    ]
    assert response.flatten("") == {
        "ResponseTime": "-1",
        "RouteHops.1.Host": "gw",
        "RouteHops.2.Host": "core",
    }
    boot = events["Device.Boot!"]
    assert boot.__name__ == "Device_Boot_Event" and list(boot.model_fields) == ["CommandKey"]
    assert boot.from_flat({"CommandKey": "k"}).CommandKey == "k"


def test_command_and_event_paths(usp: object) -> None:
    device = importlib.import_module("miniusp.models.paths").Device
    trace = device.TraceRoute
    assert isinstance(trace, CommandPath)
    assert str(trace) == "Device.TraceRoute()" and trace.definition.is_async
    assert str(device.child("Reboot()")) == "Device.Reboot()"
    # the parameter Reboot and the command Reboot() share a bare name
    assert str(device.Reboot) == "Device.Reboot" and str(device.Reboot_) == "Device.Reboot()"
    assert isinstance(device.Reboot_, CommandPath)
    boot = device.Boot
    assert isinstance(boot, EventPath)
    assert str(boot) == "Device.Boot!" and boot.definition.version == "2.0"
    stub = Path(usp.__file__).with_name("paths.pyi").read_text()  # type: ignore[attr-defined]
    assert "    TraceRoute: CommandPath" in stub and "    Boot: EventPath" in stub
    assert "    Reboot: ParamPath[str]" in stub and "    Reboot_: CommandPath" in stub


def test_shipped_tr181_usp_commands() -> None:
    from bbfmodels.tr181_usp import COMMANDS, EVENTS
    from bbfmodels.tr181_usp.paths import Device

    assert len(COMMANDS) > 200 and len(EVENTS) > 50
    _, trace_out = COMMANDS["Device.IP.Diagnostics.TraceRoute()"]
    response = trace_out.from_flat({"Status": "Complete", "RouteHops.1.RTTimes": "1,2,3"})
    assert response.Status == "Complete" and response.RouteHops[1].RTTimes == [1, 2, 3]
    assert str(Device.IP.Diagnostics.TraceRoute) == "Device.IP.Diagnostics.TraceRoute()"
    assert str(Device.Boot) == "Device.Boot!"
    assert "Device.Reboot()" in COMMANDS and "Device.Boot!" in EVENTS
