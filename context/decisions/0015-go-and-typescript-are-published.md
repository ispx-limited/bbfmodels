# 0015: The Go types and the TypeScript declarations are published on every release

## Context

Decisions 0013 and 0014 left the Go types generated on demand and the
TypeScript declarations attached to releases as files. Both are the right
first step and the wrong final one: a Go program imports a module path and
a TypeScript project installs a package, and neither wants to run a Python
tool first. Each needs its own publishing surface, because Go modules are
fetched from a repository and npm packages from the registry.

## Decision

- **A Go module repository, written only by the release.**
  `github.com/ispx-limited/bbfmodels-go` holds one package per shipped
  document (`tr181usp`, `tr098`, `tr104cwmp`, ...) under one `go.mod`. The
  release workflow regenerates every package, replaces the repository's
  content, commits and tags the same version as bbfmodels, so
  `go get github.com/ispx-limited/bbfmodels-go/tr181usp@v0.8.0` matches
  `pip install bbfmodels==0.8.0`. Nothing is edited in that repository by
  hand and its README says so; issues go to bbfmodels.
- **An npm package, `@ispx/bbfmodels`, of declarations only.** Scoped to
  the ispx organisation on npm, one module per document as a subpath export
  (`@ispx/bbfmodels/tr181_usp`), `package.json` with `exports` and no
  runtime code. Published by the release workflow with provenance,
  authenticated by a granular access token held as a repository secret,
  because npm requires either two-factor authentication or such a token to
  publish and will not create a package through trusted publishing. The
  first two versions were published from a workstation with that token;
  every later one comes from the workflow.
- **One builder for both.** `bbfmodels distribute go|npm` assembles either
  tree from the pinned documents with a version stamp, and the tests build
  both, so a release cannot ship a module that does not vet or a package
  whose exports do not match the shipped documents.

## Consequences

- Three surfaces carry the same version: PyPI, npm and the Go module repo.
  The release notes and the Discord announcement remain bbfmodels', since
  the others are generated from it.
- The Go repository's history is a sequence of releases, one commit each,
  which is what a module consumer wants to see.
