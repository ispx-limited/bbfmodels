# 0003: Parse the Forum's flattened full documents

## Context

The Forum publishes each model two ways. The modular files (`tr-181-2-21-0-cwmp.xml`)
import other files and assemble objects from reusable components, and a
reader has to resolve imports, component references and the data type
definitions in `tr-106-types.xml` across files. The flattened files
(`tr-181-2-21-0-cwmp-full.xml`) have all of that resolved: every object
carries its parameters inline and every named data type is defined in the
same document.

## Decision

The parser reads the flattened `-full.xml` editions only. A document that
still contains `<import>` or `<component>` elements is rejected with a
message that names the flattened edition.

The published files are not always well-formed XML (bare ampersands and
literal `<OUI>` markup in descriptions, one attribute published as
`value="""`). The parser repairs exactly those faults before the standard
library parser reads the text, so a failure afterwards means the file is
genuinely not a data model document.

## Consequences

- No import resolution, no component expansion, no cross-file type lookup.
  The parser is a few hundred lines and stays that way.
- Vendor documents in the TR-106 schema must be supplied flattened as well.
  The Forum's own report tool produces that form.
- The repair step is a list of known faults, not a lenient parser. A new
  fault in a published document is added to the list with a test.
