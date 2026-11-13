# Gatekeeper Rules

1. **Active Missing-Parameter Gatekeeping:**
   - The gatekeeper inspects `calculation_intent` and verifies that all mandatory boundary conditions from `config/schemas_reference.json` exist in `AircraftDesignState`.
   - If any mandatory parameter is missing (`None`), pipeline execution MUST halt immediately (`state.pipeline_status = "HALTED_MISSING_PARAMS"`).
   - Under no circumstances shall the system guess or fabricate missing boundary conditions.

2. **Stateful Multi-Turn Retention:**
   - Non-`None` parameters extracted in previous turns must be preserved across conversation turns unless explicitly overridden by the user.

3. **Passenger Count & Regulatory Classification:**
   - Record `passenger_count` for Part 23/25 routing.
   - If `passenger_count` is provided without gross mass, do not assume gross mass unless explicitly authorized or standard ISA sea-level defaults are confirmed.

4. **Zero-Math Extraction:**
   - The LLM extraction prompt must only extract raw numbers and unit strings verbatim from the user text without modifying or converting units.

5. **Conceptual Regulatory Q&A (`regulatory_qa`):**
   - For conceptual questions regarding FAA Part 23/25 or airworthiness standards, route directly to `regulatory_qa`, clear previous numerical solutions, and ground responses using authoritative regulatory citations without prompting for geometry.

6. **Extraterrestrial Atmosphere Boundary:**
   - Any query involving non-Earth planetary atmospheres (Mars, Venus, Titan, etc.) or spaceflight/orbital mechanics must immediately halt with `out_of_scope` (`OUT_OF_SCOPE_HALT`), as AeroSandbox ISA models Earth atmospheric flight exclusively.


