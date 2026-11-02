# Typed paths

Most code that talks to an ACS or a USP controller never builds a tree of
values. It asks an API for `Device.WiFi.SSID.1.SSID` by name and reads a
string back. Typed paths make that name a chain of attributes an editor
completes and a type checker verifies, with no model involved:

```python
from bbfmodels.tr181_cwmp.paths import Device

str(Device.WiFi.SSID[1].SSID)              # 'Device.WiFi.SSID.1.SSID'
str(Device.IP.Interface[1].IPv4Address[2].IPAddress)
Device.WiFi.Radio[2].Channel == "Device.WiFi.Radio.2.Channel"   # True
```

Every shipped package has a `paths` module whose root is the model's root
object. A table is indexed by instance number; the table itself renders as
the partial path CWMP uses to ask for all of it, and `search` gives the USP
search path:

```python
str(Device.WiFi.Radio)          # 'Device.WiFi.Radio.'
Device.WiFi.Radio.search        # 'Device.WiFi.Radio.*.'
Device.WiFi.Radio.schema_path   # 'Device.WiFi.Radio.{i}.'
```

A path knows its definition in the shipped schema, so the type, access,
constraints and description of a parameter are one attribute away:

```python
channel = Device.WiFi.Radio[1].Channel
channel.definition.syntax.base_type        # <BaseType.UNSIGNED_INT: 'unsignedInt'>
channel.definition.access                  # <Access.READ_WRITE: 'readWrite'>
channel.definition.syntax.facets.ranges    # (Range(min_inclusive=1, max_inclusive=255, step=None),)
channel.definition.description[:60]
Device.WiFi.Radio.definition.num_entries_parameter   # 'RadioNumberOfEntries'
```

Paths compare and hash as their string, so they work as dictionary keys
and in sets alongside plain strings.

## Editors and type checkers

At runtime one generic class walks the schema, so the `paths` module is
three lines and costs nothing to import. Beside it, `paths.pyi` is a stub
that declares every object and parameter with the Python type of its
value, which is what the editor completes and the type checker reads:

```python
class WiFi_RadioPath(ObjectPathBase):
    Enable: ParamPath[bool]
    Channel: ParamPath[int]
    SupportedFrequencyBands: ParamPath[list[str]]
    Stats: WiFi_Radio_StatsPath
```

A typo is caught twice: the type checker rejects `Device.WiFi.Radioo`, and
at runtime it raises `AttributeError` naming the object that has no such
member.

## Names the schema does not know

A vendor parameter whose document was not generated is reached
explicitly, so a typo in a standard name is never silently taken for one:

```python
str(Device.WiFi.Radio[1].child("X_ACME_TxPower"))   # 'Device.WiFi.Radio.1.X_ACME_TxPower'
```

Generate the vendor's document instead and the name completes like any
other; see [vendor models](vendor-models.md). A Forum name that is not a
Python identifier is exposed the way the models expose it, `N11kEnable` for
`11kEnable`, and renders the Forum's spelling.

## Service models

A service model's root is a table, and the document does not say where a
device mounts it, so its paths render from the document's root. Prefix the
mount when calling an API:

```python
from bbfmodels.tr104_cwmp.paths import VoiceService

str(VoiceService[1].Capabilities.MaxLineCount)   # 'VoiceService.1.Capabilities.MaxLineCount'
"Device.Services." + str(VoiceService[1].Capabilities.MaxLineCount)
```
