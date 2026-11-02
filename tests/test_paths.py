from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from bbfmodels import generate
from bbfmodels.paths import ObjectPath, ParamPath, TablePath

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def mini(tmp_path_factory: pytest.TempPathFactory) -> tuple[ObjectPath, str]:
    root = tmp_path_factory.mktemp("paths")
    generate.write_package("minipaths.cwmp", FIXTURES / "mini-cwmp-full.xml", root)
    (root / "minipaths" / "__init__.py").write_text("")
    sys.path.insert(0, str(root))
    try:
        module = importlib.import_module("minipaths.cwmp.paths")
    finally:
        sys.path.pop(0)
    stub = (root / "minipaths" / "cwmp" / "paths.pyi").read_text()
    return module.Device, stub


def test_paths_render_and_resolve(mini: tuple[ObjectPath, str]) -> None:
    device, _ = mini
    channel = device.Radio[2].Channel
    assert isinstance(channel, ParamPath)
    assert str(channel) == "Device.Radio.2.Channel" and channel.path == str(channel)
    assert channel.schema_path == "Device.Radio.{i}.Channel"
    assert channel.definition.syntax.facets.units == "channel"
    assert f"{device.RadioNumberOfEntries}" == "Device.RadioNumberOfEntries"
    radios = device.Radio
    assert isinstance(radios, TablePath)
    assert str(radios) == "Device.Radio." and radios.schema_path == "Device.Radio.{i}."
    assert radios.search == "Device.Radio.*."
    assert radios.definition.num_entries_parameter == "RadioNumberOfEntries"
    assert str(device.Radio[1]) == "Device.Radio.1."
    assert device.Radio[1].definition.path == "Device.Radio.{i}."


def test_paths_compare_as_strings(mini: tuple[ObjectPath, str]) -> None:
    device, _ = mini
    assert device.Radio[1].Enable == "Device.Radio.1.Enable"
    assert device.Radio[1].Enable == device.Radio[1].Enable
    assert device.Radio[1].Enable != device.Radio[2].Enable
    assert len({device.Radio[1].Enable, device.Radio[1].Enable}) == 1
    assert repr(device.Radio[1].Enable) == "ParamPath('Device.Radio.1.Enable')"


def test_unknown_names_and_vendor_children(mini: tuple[ObjectPath, str]) -> None:
    device, _ = mini
    with pytest.raises(AttributeError, match="no parameter or object 'Radioo'"):
        _ = device.Radioo
    with pytest.raises(TypeError):
        device.Radio["1"]  # type: ignore[index]
    with pytest.raises(TypeError):
        device.Radio[0]
    assert str(device.Radio[1].child("X_ACME_TxPower")) == "Device.Radio.1.X_ACME_TxPower"
    assert str(device.Radio[1].N11kEnable) == "Device.Radio.1.11kEnable"
    assert str(device.Radio[1].child("11kEnable")) == "Device.Radio.1.11kEnable"
    assert str(device.Config[3].Name) == "Device.Config.3.Name"


def test_stub_declares_every_name_with_its_type(mini: tuple[ObjectPath, str]) -> None:
    _, stub = mini
    assert "class DevicePath(ObjectPathBase):" in stub
    assert "    Radio: TablePath[RadioPath]" in stub
    assert "    Config: TablePath[ConfigPath]" in stub
    assert "    Channel: ParamPath[int]" in stub
    assert "    Enable: ParamPath[bool]" in stub
    assert "    Standards: ParamPath[list[str]]" in stub
    assert "    N11kEnable: ParamPath[bool]" in stub
    assert stub.rstrip().endswith("Device: DevicePath")


def test_shipped_paths() -> None:
    from bbfmodels.tr104_cwmp.paths import VoiceService
    from bbfmodels.tr181_cwmp.paths import Device

    ssid = Device.WiFi.SSID[1].SSID
    assert str(ssid) == "Device.WiFi.SSID.1.SSID"
    assert ssid.definition.access is not None and ssid.definition.access.value == "readWrite"
    assert Device.WiFi.Radio.search == "Device.WiFi.Radio.*."
    assert (
        str(VoiceService[1].Capabilities.MaxLineCount) == "VoiceService.1.Capabilities.MaxLineCount"
    )
    assert (
        str(Device.IP.Interface[1].IPv4Address[2].IPAddress)
        == "Device.IP.Interface.1.IPv4Address.2.IPAddress"
    )
