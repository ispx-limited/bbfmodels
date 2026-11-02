---
hide:
  - toc
---

<section class="ispx-home" markdown>
<div class="ispx-home__copy" markdown>

<h1 class="ispx-sr-only">bbfmodels</h1>

<p class="ispx-kicker">Typed models and schema tooling for Broadband Forum data models, so nobody hand-types TR-181 parameter paths as strings again.</p>

<div class="ispx-actions" markdown>
[Get started](guides/quickstart.md){ .ispx-btn .ispx-btn--primary }
[View on GitHub](https://github.com/ispx-limited/bbfmodels){ .ispx-btn .ispx-btn--ghost }
</div>

<div class="ispx-signal__chips">
  <span class="ispx-chip">TR-181</span>
  <span class="ispx-chip">TR-098</span>
  <span class="ispx-chip">TR-104</span>
  <span class="ispx-chip">USP commands and events</span>
</div>

</div>
</section>

## What it does

<div class="ispx-card-grid" markdown>

<div class="ispx-card" markdown>
### One parser, one representation
The published XML is read once into a normalised intermediate representation with its own JSON Schema. Every output is generated from it.
</div>

<div class="ispx-card" markdown>
### A runtime that needs no generated code
Resolve a path, validate a value against the model's constraints, and convert between the flat path and value lists on the wire and a typed tree.
</div>

<div class="ispx-card" markdown>
### Typed models and paths
pydantic models for TR-181, TR-098 and every service model, typed paths with autocomplete for code that only needs the string, and a generator for any vendor's document.
</div>

</div>

## Status

Early. `pip install bbfmodels` gives the parser, the intermediate representation, the runtime and typed models for every document the Forum publishes. Commands and events in the generated models, JSON Schema and TypeScript come next.
