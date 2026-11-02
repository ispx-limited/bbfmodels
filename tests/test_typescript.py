"""TypeScript declarations emitted from the IR."""

from __future__ import annotations

from pathlib import Path

import pytest

from bbfmodels import sources
from bbfmodels.parser import parse_file
from bbfmodels.typescript import declarations

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def cwmp() -> str:
    return declarations(parse_file(FIXTURES / "mini-cwmp-full.xml"))


def test_interfaces_properties_and_tables(cwmp: str) -> None:
    assert "export type Open<T extends string> = T | (string & {});" in cwmp
    assert "export interface Device {\n" in cwmp
    assert "  Radio?: Instances<Radio>;\n" in cwmp
    assert "  Config?: Instances<Config>;\n" in cwmp  # the Forum name, not Config_
    assert "export type Root = Device;" in cwmp
    assert "  [vendor: `X_${string}`]: Vendor;\n" in cwmp
    radio = cwmp[cwmp.index("export interface Radio {") :]
    assert "  Enable?: boolean;\n" in radio
    assert "  Channel?: number;\n" in radio
    assert '  Band?: Open<"2.4GHz" | "5GHz" | "6GHz">;\n' in radio
    assert '  Standards?: Open<"a" | "b">[];\n' in radio
    assert "  Aliases?: string[];\n" in radio
    assert "  Mode?: string;\n" in radio  # enumerationRef: no closed union
    assert '  "11kEnable"?: boolean;\n' in radio  # quoted, not sanitised


def test_descriptions_become_doc_comments(cwmp: str) -> None:
    assert "/** readWrite. Second paragraph" not in cwmp
    assert "/** readWrite */\n  Enable?: boolean;" in cwmp
    assert "/**\n * Device.Radio.{i}.\n *\n * One radio.\n" in cwmp
    assert "One radio." in cwmp
    bare = declarations(parse_file(FIXTURES / "mini-cwmp-full.xml"), descriptions=False)
    assert "One radio." not in bare and "/** readWrite */" not in bare
    assert "export interface Radio {\n  Alias?: string;\n" in bare


def test_commands_events_and_service_root() -> None:
    usp = declarations(parse_file(FIXTURES / "mini-usp-full.xml"))
    assert "export interface Device_TraceRoute_Input {" in usp
    assert "export interface Device_TraceRoute_Output_RouteHops {" in usp
    assert "  RouteHops?: Instances<Device_TraceRoute_Output_RouteHops>;\n" in usp
    assert (
        '  "Device.TraceRoute()": { input: Device_TraceRoute_Input; '
        "output: Device_TraceRoute_Output; async: true };\n"
    ) in usp
    assert '  "Device.Boot!": Device_Boot_Event;\n' in usp
    assert "/** mandatory. */" not in usp and "mandatory" in usp
    voice = declarations(parse_file(FIXTURES / "mini-service-full.xml"))
    assert "export type Root = Instances<VoiceService>;" in voice


def _cached(name: str) -> Path:
    path = sources.cache_dir() / name
    if not path.exists():
        pytest.skip(f"{name} is not in the cache; run 'bbfmodels fetch'")
    return path


def test_tr181_declarations() -> None:
    text = declarations(parse_file(_cached("tr-181-2-21-0-usp-full.xml")), descriptions=False)
    assert text.count("export interface ") > 1400
    assert "export interface WiFi_Radio {" in text
    assert (
        '  "Device.IP.Diagnostics.TraceRoute()": { input: IP_Diagnostics_TraceRoute_Input;' in text
    )
    assert "export interface Device_Boot_Event {" in text
    # no unbalanced braces: every interface opened is closed
    assert text.count("{") == text.count("}")
