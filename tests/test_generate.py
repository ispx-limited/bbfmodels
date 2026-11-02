"""The generator, on the fixture and on the shipped packages."""

from __future__ import annotations

import filecmp
import gzip
import importlib
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bbfmodels import generate, sources
from bbfmodels.model import Model

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def mini(tmp_path_factory: pytest.TempPathFactory) -> type[Model]:
    root = tmp_path_factory.mktemp("gen")
    generate.write_package("mini.cwmp", FIXTURES / "mini-cwmp-full.xml", root)
    (root / "mini" / "__init__.py").write_text("")
    sys.path.insert(0, str(root))
    try:
        module = importlib.import_module("mini.cwmp")
    finally:
        sys.path.pop(0)
    device: type[Model] = module.Device
    return device


FLAT = {
    "Device.RadioNumberOfEntries": "2",
    "Device.Param": "p",
    "Device.Model": "m",
    "Device.Radio.1.Enable": "1",
    "Device.Radio.1.Channel": "36",
    "Device.Radio.1.Band": "5GHz",
    "Device.Radio.1.Standards": "a, b",
    "Device.Radio.1.Aliases": "x,y",
    "Device.Radio.2.Band": "7GHz",
    "Device.Radio.2.X_EXAMPLE_Power": "high",
    "Device.X_EXAMPLE_Thing.1.Foo": "bar",
    "Device.X_EXAMPLE_Single.Baz": "1",
    "Device.Config.1.Name": "first",
}


def test_generated_package_shape(mini: type[Model]) -> None:
    assert mini.__name__ == "Device" and mini.bbf_path == "Device."
    assert mini.bbf_package == "mini.cwmp"
    radio = mini.model_fields["Radio"]
    assert "dict[int," in str(radio.annotation)
    assert set(mini.model_fields) >= {"RadioNumberOfEntries", "Param", "Model", "Radio", "Config_"}
    assert mini.model_fields["Config_"].alias == "Config"


def test_from_flat_and_back(mini: type[Model]) -> None:
    device = mini.from_flat(FLAT)
    radios = device.Radio  # type: ignore[attr-defined]
    assert sorted(radios) == [1, 2]
    one = radios[1]
    assert one.Enable is True and one.Channel == 36 and one.Band == "5GHz"
    assert one.Standards == ["a", "b"] and one.Aliases == ["x", "y"]
    assert radios[2].Band == "7GHz"  # a value outside the enumeration is kept
    assert radios[2].X_EXAMPLE_Power == "high"
    assert device.X_EXAMPLE_Thing == {"1": {"Foo": "bar"}}  # type: ignore[attr-defined]
    assert device.Param == "p" and device.Model == "m"  # type: ignore[attr-defined]
    assert device.Config_[1].Name == "first"  # type: ignore[attr-defined]
    flat = device.flatten()
    assert flat["Device.Config.1.Name"] == "first"
    assert flat["Device.Radio.1.Enable"] == "true"  # canonical, not the "1" that came in
    assert flat["Device.Radio.1.Standards"] == "a,b"
    assert flat["Device.X_EXAMPLE_Thing.1.Foo"] == "bar"
    assert flat["Device.X_EXAMPLE_Single.Baz"] == "1"
    assert mini.from_flat(flat).flatten() == flat


def test_relative_paths_and_problems(mini: type[Model]) -> None:
    device = mini.from_flat(
        {"Radio.1.Channel": "999", "Radio.1.Band": "7GHz", "Radio.2.Enable": "0"}
    )
    assert device.Radio[1].Channel == 999  # type: ignore[attr-defined]
    assert device.problems() == [
        ("Device.Radio.1.Channel", "999 is outside the allowed ranges"),
        ("Device.Radio.1.Band", "'7GHz' is not one of the enumerated values"),
    ]


def test_typed_construction(mini: type[Model]) -> None:
    radio_cls = type(mini.from_flat({"Radio.1.Enable": "1"}).Radio[1])  # type: ignore[attr-defined]
    radio = radio_cls(Enable=False, Channel=11, Standards=["a"])
    assert radio.flatten("Device.Radio.5.") == {
        "Device.Radio.5.Enable": "false",
        "Device.Radio.5.Channel": "11",
        "Device.Radio.5.Standards": "a",
    }
    with pytest.raises(ValueError):
        radio_cls(Channel="eleven")


def test_lenient_types(mini: type[Model]) -> None:
    device = mini.from_flat({"Radio.1.Enable": "true"})
    assert device.Radio[1].Enable is True  # type: ignore[attr-defined]
    with pytest.raises(ValueError):
        mini.from_flat({"Radio.1.Enable": "yes"})


def _cached(name: str) -> Path:
    path = sources.cache_dir() / name
    if not path.exists():
        pytest.skip(f"{name} is not in the cache; run 'bbfmodels fetch'")
    return path


@pytest.mark.parametrize(("package", "document"), sorted(generate.PACKAGES.items()))
def test_shipped_packages_are_current(package: str, document: str, tmp_path: Path) -> None:
    """Regenerating a shipped package reproduces the committed files exactly."""
    generate.write_package(package, _cached(document), tmp_path)
    fresh = tmp_path.joinpath(*package.split("."))
    committed = Path(__file__).parent.parent / "src" / Path(*package.split("."))
    fresh_files = sorted(p.name for p in fresh.iterdir())
    committed_files = sorted(p.name for p in committed.iterdir() if p.name != "__pycache__")
    assert fresh_files == committed_files
    stale = [n for n in fresh_files if not _same(fresh / n, committed / n)]
    assert stale == [], f"run 'make generate': {stale}"


def _same(a: Path, b: Path) -> bool:
    # The archive's bytes depend on the zlib build; its content does not.
    if a.suffix == ".gz":
        return gzip.decompress(a.read_bytes()) == gzip.decompress(b.read_bytes())
    return filecmp.cmp(a, b, shallow=False)


def test_tr181_models_on_device_values() -> None:
    from bbfmodels.tr181_cwmp import Device

    device = Device.from_flat(
        {
            "Device.DeviceInfo.ManufacturerOUI": "00AABB",
            "Device.DeviceInfo.UpTime": "1234",
            "Device.DeviceInfo.FirstUseDate": "2026-01-02T03:04:05Z",
            "Device.WiFi.Radio.1.Enable": "1",
            "Device.WiFi.Radio.1.Channel": "36",
            "Device.WiFi.Radio.1.SupportedFrequencyBands": "2.4GHz,5GHz",
            "Device.WiFi.Radio.1.X_EXAMPLE_TxPower": "high",
            "Device.WiFi.SSID.1.LowerLayers": "Device.WiFi.Radio.1",
            "Device.X_EXAMPLE_Thing.1.Foo": "bar",
        }
    )
    assert device.DeviceInfo is not None and device.WiFi is not None
    assert device.DeviceInfo.UpTime == 1234
    assert device.DeviceInfo.FirstUseDate == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    radio = device.WiFi.Radio[1]
    assert radio.Enable is True and radio.Channel == 36
    assert radio.SupportedFrequencyBands == ["2.4GHz", "5GHz"]
    assert device.WiFi.SSID[1].LowerLayers == ["Device.WiFi.Radio.1"]
    assert device.problems() == []
    flat = device.flatten()
    assert flat["Device.WiFi.Radio.1.X_EXAMPLE_TxPower"] == "high"
    assert flat["Device.X_EXAMPLE_Thing.1.Foo"] == "bar"
    assert Device.from_flat(flat).flatten() == flat


def test_tr181_import_stays_fast() -> None:
    for name in ("bbfmodels.tr181_cwmp", "bbfmodels.tr181_usp", "bbfmodels.tr098"):
        sys.modules.pop(name, None)
    for name in [m for m in sys.modules if m.startswith("bbfmodels.tr181_cwmp")]:
        del sys.modules[name]
    start = time.perf_counter()
    importlib.import_module("bbfmodels.tr181_cwmp")
    assert time.perf_counter() - start < 3.0
