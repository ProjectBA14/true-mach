# True-Mach (AeroGuard-RAG)
### Autonomous Neuro-Symbolic Aerodynamic Design & Airworthiness Compliance Engine

True-Mach (AeroGuard-RAG) is a dual-core aerospace engineering system combining **deterministic symbolic aerodynamic solvers** (AeroSandbox, SymPy, Pint) with **hybrid knowledge graph & vector retrieval** (LightRAG) over FAA Airworthiness Regulations (14 CFR Part 23 & Part 25) and NASA aerodynamic technical reports.

---

## 🚀 Key Architectural Pillars

1. **Zero LLM Math Guarantee**:
   - LLMs are strictly restricted to intent parsing, query formulation, and prose synthesis.
   - All physical unit conversions run deterministically inside `pint.UnitRegistry`.
   - All flight dynamics equations (lift, induced drag, stall speed, Prandtl-Glauert compressibility correction, Korn drag divergence, and Lock wave drag) execute in SymPy and AeroSandbox with exact symbolic substitutions.

2. **Autonomous Regulatory Classification**:
   - Dynamically classifies aircraft into **FAA 14 CFR Part 23** (Normal/Commuter, $\le 19$ pax, $\le 8,618.3\text{ kg}$) or **FAA 14 CFR Part 25** (Transport Category, $> 19$ pax or $> 19,000\text{ lbs}$).
   - Applies strict airworthiness thresholds:
     - Part 23 Landing Stall Speed: $V_{s0} \le 61\text{ kts}$ (14 CFR § 23.2110 / § 23.49).
     - Part 25 Approach Envelope: $V_{s0} \le 145\text{ kts}$ (14 CFR § 25.103).
     - Subsonic Induced Drag Efficiency: $C_{Di} \le 0.040$ (NASA SP-367).
     - Transonic Buffet & Drag Divergence: $M_\infty \le M_{dd}$ (14 CFR § 25.253 / NASA NTRS 20060008908).

3. **Active Counter-Questioning Gatekeeper**:
   - Inspects design state against mandatory boundary conditions for each calculation intent.
   - Halts execution with structured engineering counter-questions if parameters are missing, preventing ungrounded assumptions.
   - Supports conceptual inquiry routing (`regulatory_qa`) and automated planform optimization (`wing_sizing`).

4. **Deterministic AeroSandbox Parameter Sweep Advisor**:
   - When a design incurs a compliance `WARNING` or `FAIL`, the engine executes a deterministic parameter sweep in AeroSandbox (e.g., wingspan $b$, planform area $S$, or wing sweep angle $\Lambda$).
   - Computes exact trajectories and prescribes minimal compliant modifications with zero hallucination.

5. **Verbatim Grounded Citations**:
   - Retrieval queries LightRAG across indexed FAA/NASA corpus and surfaces verbatim excerpts, report numbers, and document titles.

---

## 📁 Repository Structure

```
.
├── config/
│   └── schemas_reference.json     # Intent schemas, thresholds & mandatory parameter definitions
├── data/
│   ├── lightrag_storage/          # Indexed LightRAG Knowledge Graph & Vector DB
│   ├── parsed_markdown/           # High-fidelity parsed FAA & NASA reference texts
│   └── raw_pdfs/                  # Raw FAA / NASA technical documents
├── Docs/                          # Original NASA & FAA engineering source PDFs
├── Rules/                         # System rules, math protocols, & citation constraints
├── src/
│   ├── gatekeeper/
│   │   ├── clarifier.py           # Intent extraction, boundary condition inspection & counter-questioning
│   │   └── schemas.py             # Pydantic data schemas for design states & compliance reports
│   ├── ingestion/
│   │   └── build_index.py         # LightRAG pipeline for chunking, embedding, & entity extraction
│   ├── physics_engine/
│   │   ├── aero_solver.py         # Deterministic Pint, SymPy, & AeroSandbox physical solvers
│   │   └── compliance.py          # Regulatory rule checking & parameter-sweep optimizer
│   ├── retrieval/
│   │   └── standards_router.py    # Dual-mode retrieval, citation extraction, & classification
│   └── orchestrator.py            # Central 5-module sequential relay controller
├── tests/
│   ├── benchmark_prompts.json     # IEEE 830 test fixtures & gold-standard benchmarks
│   └── test_acceptance.py         # Full acceptance test suite (TC-01 through TC-06 + regressions)
├── app.py                         # Single-column Gemini-style Streamlit application
├── requirements.txt               # Pinned Python package dependencies
├── Rules.md                       # Core neuro-symbolic behavioral rules
└── spec.md                        # Formal engineering requirements specification
```

---

## 🛠️ Setup & Installation

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Git

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/ProjectBA14/true-mach.git
cd true-mach

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. API Keys Configuration
Create a `.env` file in the repository root (see `.env.example`):
```env
Gemini_APIKEY=your_google_ai_studio_api_key
GROQ_APIKEY=your_groq_api_key
```
*(Note: A local deterministic fallback parser is built-in; the local test suite consumes zero API tokens).*

---

## 🧪 Running Tests

Run the complete 18-point verification and regression acceptance test suite:
```bash
pytest tests/test_acceptance.py -v
```

---

## 💻 Launching the Application

Start the interactive Streamlit dark workspace:
```bash
streamlit run app.py
```
Then navigate to `http://localhost:8501`.

