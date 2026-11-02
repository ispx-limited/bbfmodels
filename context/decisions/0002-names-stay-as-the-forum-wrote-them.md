# 0002: Names stay as the Forum wrote them

## Context

Generated attributes could follow each language's naming convention
(`ssid_advertisement_enabled` in Python) or keep the Forum's PascalCase
(`SSIDAdvertisementEnabled`). Converting is lossy and ambiguous:
`IPv6Address`, `X_EXAMPLE-COM_Foo`, `DHCPv4` and `WANPPPConnection` have no
single correct snake_case, and the conversion cannot be reversed reliably.
Every ACS log, every vendor document and every page of the specification
uses the original spelling.

## Decision

Objects, parameters, commands and events keep their PascalCase spelling
verbatim in every generated language. Multi-instance objects keep `{i}` in
schema paths, as the specification writes them; a data path on a device
replaces `{i}` with the instance number. In code a table is indexed:
`device.WiFi.SSID[1].SSID` renders the path `Device.WiFi.SSID.1.SSID`.
The `*` wildcard never appears in the model. It is only emitted when a USP
search path is built, because that is the one place the protocol defines
it.

## Consequences

- Generated Python does not follow PEP 8 attribute naming, on purpose, and
  linters are configured to accept that in generated modules.
- A name can be searched for in the specification, a device dump or a log
  and found in the code unchanged.
- Vendor extension names (`X_<OUI>_Name`) need no mangling beyond what the
  target language's identifier rules force, and that mangling is recorded
  in the IR so it is reversible.
