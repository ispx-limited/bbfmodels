# Changelog

## [0.6.0](https://github.com/ispx-limited/bbfmodels/compare/v0.5.0...v0.6.0) (2026-11-02)


### Added

* **typescript:** TypeScript declarations of every model from the IR, attached to each release ([#26](https://github.com/ispx-limited/bbfmodels/issues/26)) ([6a99d5d](https://github.com/ispx-limited/bbfmodels/commit/6a99d5d3584bb7350c69635c9fa6150b0d1c9f1f))

## [0.5.0](https://github.com/ispx-limited/bbfmodels/compare/v0.4.0...v0.5.0) (2026-11-02)


### Added

* **schema:** JSON Schema of every model from the IR, attached to each release ([#23](https://github.com/ispx-limited/bbfmodels/issues/23)) ([6261c98](https://github.com/ispx-limited/bbfmodels/commit/6261c9855ef6bc21ae2c9002601d6d2ba4e0d6db))

## [0.4.0](https://github.com/ispx-limited/bbfmodels/compare/v0.3.0...v0.4.0) (2026-11-02)


### Added

* **models:** USP commands and events as classes and paths, and the xsi:type a CWMP stack needs ([#20](https://github.com/ispx-limited/bbfmodels/issues/20)) ([eca0c46](https://github.com/ispx-limited/bbfmodels/commit/eca0c46a10c6fc205dbc198d051dbb860f321003))

## [0.3.0](https://github.com/ispx-limited/bbfmodels/compare/v0.2.1...v0.3.0) (2026-11-02)


### Added

* **paths:** typed paths with autocomplete for every model, no pydantic model needed ([#17](https://github.com/ispx-limited/bbfmodels/issues/17)) ([ba3a7b7](https://github.com/ispx-limited/bbfmodels/commit/ba3a7b7781129477aed7ee015d51f9079521b331))

## [0.2.1](https://github.com/ispx-limited/bbfmodels/compare/v0.2.0...v0.2.1) (2026-11-02)


### Fixed

* **models:** generated files no longer record the tool version, which broke the release build ([#10](https://github.com/ispx-limited/bbfmodels/issues/10)) ([ab909c7](https://github.com/ispx-limited/bbfmodels/commit/ab909c7d67b102b11f09122d8c01cea674859e8c))
* **parser:** a vendor document's empty syntax is read as a string instead of failing ([#11](https://github.com/ispx-limited/bbfmodels/issues/11)) ([7cdb4a1](https://github.com/ispx-limited/bbfmodels/commit/7cdb4a1c4fa39b7741c90a67c84b43812c889fe2))
* **parser:** a vendor document's unknown vocabulary values fall back with a warning instead of failing ([#13](https://github.com/ispx-limited/bbfmodels/issues/13)) ([bb3e807](https://github.com/ispx-limited/bbfmodels/commit/bb3e80723320fdd69d2b2263ef066d790a28feb2))

## [0.2.0](https://github.com/ispx-limited/bbfmodels/compare/v0.1.0...v0.2.0) (2026-11-02)


### Added

* **models:** generated pydantic models for every published data model, and a generator for any document ([#7](https://github.com/ispx-limited/bbfmodels/issues/7)) ([adf73f2](https://github.com/ispx-limited/bbfmodels/commit/adf73f2004eb7cf24673a52298a251af45f39364))

## 0.1.0 (2026-11-02)


### Added

* **parser:** read a published document into the intermediate representation ([#1](https://github.com/ispx-limited/bbfmodels/issues/1)) ([462d045](https://github.com/ispx-limited/bbfmodels/commit/462d04530a7d3a7d62a3da440404f4afcadb2c4f))
* **runtime:** resolve paths, hold a device's values and validate them against the schema ([#3](https://github.com/ispx-limited/bbfmodels/issues/3)) ([35146ad](https://github.com/ispx-limited/bbfmodels/commit/35146adb52757ac9a05836415f87815135c55b94))
