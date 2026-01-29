# Design Changelog

All notable changes to the system design documents will be documented in this file.

## [1.1] - 2026-01-27
### Modified
- **techstack-plan.md**:
  - Updated version to 1.1 (Hardware-Optimized Draft).
  - **Runtime**: Changed device from `cpu` to `mps` to leverage Apple Silicon acceleration.
  - **Data Pipeline**: Added "Context Injection" (Header Propagation) and "Metadata Extraction" (Scenario Tags) to align with PRD v1.2 data constraints.
  - **Memory**: Clarified MVP memory strategy as "Sliding Window (Session DB)".

## [1.0] - 2026-01-27
### Added
- **techstack-plan.md**: Initial draft created.
