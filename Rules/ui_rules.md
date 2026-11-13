# Split-Screen UI Rules

1. **50/50 Split Screen:**
   - Left Column: Interactive conversational chat with parameter pills and session reset.
   - Right Column: Live verification dashboard with compliance status banner, unit conversion table, symbolic equation traces, conditional advisory card (hidden on PASS), and expandable regulatory citations.

2. **Immutable Solver Data Binding:**
   - The Right Panel must bind exclusively to deterministic Python objects (`PhysicsSolutionBundle`, `ComplianceReport`, `RegulatoryCitation`), never parsing LLM narrative text.

3. **Status Badges:**
   - PASS: `#16A34A` Emerald Green.
   - WARNING: `#D97706` Amber Yellow.
   - FAIL: `#DC2626` Crimson Red.
   - AWAITING_PARAMETERS: `#2563EB` Slate Blue.

