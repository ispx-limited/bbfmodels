# Vendor models

Vendors extend the standard models with `X_<OUI>_` objects and parameters,
and the generated standard packages keep those as untyped extras. For typed
access, generate a package from the vendor's own document. This guide
walks through a real one: a gateway maker's TR-098 export with 267 objects,
159 of them vendor extensions under `X_0000C5_`.

## The document

A vendor document is XML in the same TR-106 schema the Forum uses, with
the standard objects and the vendor's additions in one tree. Some vendors
publish it; for others it is exported from the device or produced by the
Forum's report tool from the vendor's modular files. Either way bbfmodels
reads the flattened form: one file, no `<import>`, no `<component>`.

Check it parses before generating:

```sh
bbfmodels ir nvg578lx-igd-datamodel.xml -o /dev/null
```

Documents captured from devices depart from the schema in small ways, and
the parser says where it had to decide:

```
ParseWarning: InternetGatewayDevice.LANDevice.{i}.Hosts.Host.{i}.X_0000C5_LastActive: 'forceDefaultPolled' is not a ActiveNotify; read as 'normal'
ParseWarning: InternetGatewayDevice.WANDevice.{i}.X_0000C5_WANOpticalInterfaceConfig.GPON.SerialNumber has a syntax without a type; treated as a string
```

Each warning names the parameter and the reading taken. Anything the
parser cannot work around is a `ParseError` with the place, and the
[documents guide](documents.md) lists what it tolerates.

## Generating

```sh
bbfmodels generate nvg578lx-igd-datamodel.xml --package acme.nvg578lx --root src
```

`--package` is the dotted Python package to create and `--root` the
source directory to create it under; `src/acme/nvg578lx/` appears with one
module per top-level subtree, a root module, `__init__.py` and the IR as
`ir.json.gz`. Create `src/acme/__init__.py` if the parent package does
not exist yet.

```
src/acme/nvg578lx/
├── __init__.py              InternetGatewayDevice, SOURCE, SPEC, MODEL, schema()
├── internetgatewaydevice.py the root class
├── deviceinfo.py            InternetGatewayDevice.DeviceInfo.* including X_0000C5_CPUStatistics
├── landevice.py             InternetGatewayDevice.LANDevice.*
├── wandevice.py             ...
└── ir.json.gz
```

The root class is named after the root object, here `InternetGatewayDevice`,
even when the vendor named the model `InternetGatewayDevice_9.5.0h5d40:2.0`.

## Using it

```python
from acme.nvg578lx import InternetGatewayDevice, schema

igd = InternetGatewayDevice.from_flat({
    "InternetGatewayDevice.DeviceInfo.UpTime": "4321",
    "InternetGatewayDevice.DeviceInfo.X_0000C5_CPUStatistics.AverageUtilization": "17",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.SSID": "home",
    "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.Channel": "6",
    "InternetGatewayDevice.LANDevice.1.Hosts.Host.1.X_0000C5_LastActive": "2026-01-02T03:04:05Z",
})
igd.DeviceInfo.X_0000C5_CPUStatistics.AverageUtilization   # '17', typed as the vendor declared it
igd.LANDevice[1].WLANConfiguration[1].Channel               # 6
igd.LANDevice[1].Hosts.Host[1].X_0000C5_LastActive          # '2026-01-02T03:04:05Z'
igd.problems()                                              # []
igd.flatten()                                               # every path, vendor ones included
```

The vendor's extensions are ordinary typed fields now, and their classes
are importable: `from acme.nvg578lx.deviceinfo import DeviceInfo_X_0000C5_CPUStatistics`.
Parameters from a different vendor, or from a newer firmware than the
document describes, are still kept as extras.

Two things are only as good as the document. `AverageUtilization` above is
a string because the vendor declared it a string, and `Channel` accepts
`200` without complaint because the vendor declared no range. `schema()`
answers what the document says about any path:

```python
s = schema()
s.parameter("InternetGatewayDevice.LANDevice.{i}.WLANConfiguration.{i}.Channel").syntax.facets.ranges   # ()
sorted(p for p in s.objects if "X_0000C5" in p)[:3]
```

## Keeping it current

Commit the generated package to the repository that uses it and regenerate
when the vendor's document changes. A test like this fails when the
committed package is stale:

```python
import filecmp, gzip
from pathlib import Path
from bbfmodels.generate import write_package

def test_vendor_package_is_current(tmp_path: Path) -> None:
    write_package("acme.nvg578lx", Path("vendor/nvg578lx-igd-datamodel.xml"), tmp_path)
    fresh = tmp_path / "acme" / "nvg578lx"
    committed = Path("src/acme/nvg578lx")
    for file in fresh.iterdir():
        if file.suffix == ".gz":
            assert gzip.decompress(file.read_bytes()) == gzip.decompress((committed / file.name).read_bytes())
        else:
            assert filecmp.cmp(file, committed / file.name, shallow=False), file.name
```

The archive is compared by content because gzip output differs between
zlib builds; the generator leaves an unchanged archive untouched for the
same reason.
