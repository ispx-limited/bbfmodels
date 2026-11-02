# 0004: Generated output is committed and checked for drift

## Context

Generated bindings can be produced at build time from downloaded XML, or
generated once and committed. Build-time generation keeps the repository
small but makes every install depend on the Forum's site and hides the
output from review.

## Decision

Generated output is committed. CI regenerates from the pinned source
documents and fails when the committed output differs, so a change to the
generator or to a source document shows up as a reviewable diff in the same
pull request. Generated files are never edited by hand.

Each generated module records the source document and version it came from.
The package version is the tool's; a new Forum release is a change to the
pinned documents and lands by pull request like any other.

## Consequences

- `pip install bbfmodels` needs no network access beyond PyPI.
- Reviewers see exactly what a generator change does to the output.
- The repository carries generated code that is large. That is accepted;
  it is what users install.
