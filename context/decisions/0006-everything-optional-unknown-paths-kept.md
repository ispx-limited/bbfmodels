# 0006: Everything is optional and unknown paths round-trip

## Context

No device exposes the whole model. A gateway implements a subset of TR-181,
adds vendor parameters under `X_<OUI>_` names the model does not know, and
a management system usually reads a partial subtree, never the full tree.
A binding that requires every parameter, or drops what it does not
recognise, cannot hold what a real device returns.

## Decision

Every parameter and every child object in a generated model is optional.
A tree built from a device's path and value list keeps every path it did
not recognise, in the object it belongs to, and writes it back unchanged
when the tree is flattened. Unknown paths are never an error; they are
data.

## Consequences

- Validation is of what is present, never of completeness. Checking a
  device against a profile's requirements is a separate, explicit
  operation.
- Flatten after parse reproduces the input exactly, including vendor
  parameters, and the test suite asserts that round trip on real device
  exports.
