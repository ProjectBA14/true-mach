# General Instructions
* **Scope of This File:** Keep only broad, project-wide principles here. Place module-specific or domain-specific protocols (e.g., physics solver rules, RAG citation rules, UI layout rules) in dedicated `.md` files inside `Rules/` and reference them when working on those modules.
* **Autonomous Execution:** Follow `spec.md` end-to-end without pausing for confirmation unless an external API key or required source file is missing.
* **Preserve Existing Secrets & Assets:** Never overwrite `.env` or delete source PDFs in `Docs/`.

# Global Coding Standards
* **YAGNI:** Do not build speculative abstractions or features until required by `spec.md`.
* **Fail Fast:** Raise explicit, typed errors (`ValueError`, `pint.DimensionalityError`, `pydantic.ValidationError`) immediately instead of masking failures.
* **Simple First:** Implement the most direct, deterministic solution first; add complexity only when required.
* **Delete Aggressively:** Remove dead code, unused imports, and redundant boilerplate (`less code = fewer bugs`).
* **Semantic Naming:** Always name variables, parameters, classes, and endpoints with verbose, self-documenting names (e.g., `wingspan_meters`, `induced_drag_coefficient_cdi`).