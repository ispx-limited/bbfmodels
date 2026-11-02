# 0007: Vendor extensions are overlays in the same schema

## Context

Vendors extend the standard models with `X_<OUI>_` objects and parameters.
Some publish a TR-106 document describing them; for others the extension
is only visible in a device export. Users need typed access to those
extensions as much as to the standard model.

## Decision

A vendor extension is a document in the TR-106 schema, supplied by the
vendor or produced from a device export, and it generates an overlay: the
standard model's classes extended with the vendor's additions. The tool
carries no knowledge of any vendor. There are no lookup tables of OUIs,
model names or firmware versions in code, and no vendor-specific branches.

## Consequences

- Adding a vendor needs no change to this repository; a user generates
  from the vendor's document.
- The standard model's classes do not change when an overlay is applied,
  so code written against the standard model keeps working.
- A converter from a device export to a TR-106 document is in scope, since
  most vendors publish no document.
