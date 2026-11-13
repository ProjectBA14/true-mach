# IEEE Std 830-1998 Software Requirements Specification (SRS) & Master Technical Blueprint (`SPEC.md`)

**Project Title:** AeroGuard-RAG: An Autonomous Neuro-Symbolic Aerodynamic Design & Compliance Assistant  
**Document Identifier:** `SPEC-AG-RAG-2026-V1.0`  
**Academic Stage:** Final-Year Undergraduate Computer Science & Aerospace Systems Engineering Capstone — Phase-1 Evaluation Submission & Autonomous IDE Implementation Specification  
**Author / Lead Architect:** Akshay Bhaskar (Department of Computer Science and Engineering, GD Goenka University)  
**Date:** November 13, 2026  
**Target Implementation Environment:** Google Antigravity Agentic IDE (Zero-Clarification Autonomous Codebase Generation)  

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) follows the structural and analytical conventions of [IEEE Std 830-1998](https://standards.ieee.org/standard/830-1998.html) (*IEEE Recommended Practice for Software Requirements Specifications*). It serves two simultaneous operational mandates:
1. **Academic Phase-1 Evaluation Artifact:** Establishes the formal systems engineering baseline, safety-critical aviation problem statement, neuro-symbolic architectural novelty, and traceable functional/non-functional verification matrix required for a final-year undergraduate engineering capstone review.
2. **Self-Contained Agentic IDE Blueprint (`SPEC.md`):** Provides an unambiguous, deterministic implementation specification that enables an autonomous coding agent (Google Antigravity) to scaffold, implement, wire, and verify the entire `aeroguard-rag` repository end-to-end without requiring external human clarification.

### 1.2 Scope
**AeroGuard-RAG** is a local-CPU, neuro-symbolic aerodynamic design, verification, and regulatory compliance assistant. Unlike conventional Retrieval-Augmented Generation (RAG) wrappers that rely on probabilistic Large Language Models (LLMs) to both retrieve text and compute engineering mathematics, AeroGuard-RAG enforces a strict **Neuro-Symbolic Separation of Concerns**:

* **Neural Layer (Language & Graph-RAG Retrieval):** Uses offline high-fidelity document parsing via [Microsoft MarkItDown](https://github.com/microsoft/markitdown) and [PyMuPDF4LLM](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/), hybrid knowledge-graph and vector indexing via [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG/blob/main/README.md) with local CPU embeddings ([BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5)), and cloud free-tier LLM inference (`llama-3.3-70b-versatile` via Groq or `gemini-2.5-flash` via Google AI Studio) strictly limited to structured JSON parameter extraction and natural-language formatting of already-verified numerical outputs.
* **Symbolic & Deterministic Physics Layer (Gatekeeping, Dimensional Analysis & Aerodynamic Solving):** Uses [Pydantic](https://docs.pydantic.dev/) state schemas for active missing-parameter detection and counter-questioning, [Pint](https://github.com/hgrecco/pint) for strict SI dimensional homogeneity, [SymPy](https://github.com/sympy/sympy) for symbolic equation verification, and [AeroSandbox](https://github.com/peterdsharpe/AeroSandbox) for deterministic calculation and parameter-sweep design advisories.

#### 1.2.1 Industry Problem & Motivation
Major aerospace airframers (Airbus, Boeing), defense and national research laboratories (NASA, HAL, DRDO, NAL), and civil aviation authorities (FAA, EASA, DGCA) face three critical barriers that block the deployment of standard LLM-based RAG systems in preliminary aircraft design workflows:
1. **The Hallucination Liability Wall:** Standard autoregressive LLMs hallucinate floating-point arithmetic, unit conversions, material tolerances, and non-linear aerodynamic relationships. In safety-critical aviation workflows governed by [RTCA DO-178C](https://www.rtca.org/do-178/) (*Software Considerations in Airborne Systems and Equipment Certification*) and [SAE ARP4754A](https://www.sae.org/standards/arp4754b-guidelines-development-civil-aircraft-systems) (*Guidelines for Development of Civil Aircraft and Systems*), unverified probabilistic math is an immediate certification disqualifier.
2. **Silent Parameter Assumptions:** When an engineer prompts a standard chatbot with an underspecified query (e.g., *"Calculate the induced drag for a 12-meter wingspan aircraft"*), standard LLMs silently fabricate missing boundary conditions (such as cruise altitude, true airspeed, wing area, or aircraft gross mass) rather than halting to query the engineer.
3. **Complex Multi-Column Technical Corpora:** Foundational aviation corpora—such as [NASA Technical Reports Server (NTRS)](https://ntrs.nasa.gov/search.jsp?R=19760003955) monographs and [FAA 14 CFR Part 23](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-23) / [FAA 14 CFR Part 25](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-25) regulatory tables—contain dense multi-column layouts, embedded LaTeX equations, and conditional airworthiness thresholds that naive fixed-token text chunkers corrupt.

#### 1.2.2 Aerodynamic Engineering Domain Scope
AeroGuard-RAG operates across four tightly coupled sub-domains of fixed-wing aircraft aerodynamics:
* **Subsonic & Compressible Flow Regimes:** Lift generation ($L$), lift coefficient ($C_L$), induced drag coefficient ($C_{Di}$), induced drag force ($D_i$), parasitic/zero-lift drag ($C_{D0}$), Reynolds number ($Re$), Mach number ($M$), and Prandtl-Glauert compressibility corrections ($\beta = \sqrt{1 - M^2}$ for $M < 0.85$).
* **Airfoil & Wing Planform Performance:** Aspect ratio ($AR = b^2 / S$), Oswald span efficiency factor ($e$), power-off landing stall speed ($V_{s0}$), clean stall speed ($V_{s1}$), and wing loading ($W/S$).
* **Static Longitudinal Stability:** Center of gravity ($x_{cg}$) envelope bounds, aerodynamic neutral point ($x_{np}$), and static margin ($SM = (x_{np} - x_{cg}) / \bar{c}$).
* **Flight Envelope & Propulsion Performance:** International Standard Atmosphere (ISA) altitude density/temperature/pressure profiles $\rho(h), T(h), P(h)$, total thrust required ($T_R$), steady climb gradient ($\gamma$ and $\sin\gamma = (T - D)/W$), and Breguet range and endurance equations.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term / Acronym | Full Expansion / Technical Definition |
| :--- | :--- |
| **AR** | Aspect Ratio ($AR = b^2 / S$), dimensionless ratio of wingspan squared to wing planform area. |
| **ARP4754A** | [SAE Aerospace Recommended Practice 4754A](https://www.sae.org/standards/arp4754b-guidelines-development-civil-aircraft-systems), system-level development assurance standard for civil aircraft. |
| **ASB** | [AeroSandbox](https://github.com/peterdsharpe/AeroSandbox), Python library for aircraft design optimization and deterministic aerodynamic modeling. |
| **CFR** | Code of Federal Regulations (Title 14 covers Aeronautics and Space). |
| **DGCA** | Directorate General of Civil Aviation (India). |
| **DO-178C** | [RTCA DO-178C](https://www.rtca.org/do-178/), primary document by which certification authorities approve commercial airborne software. |
| **EASA** | European Union Aviation Safety Agency. |
| **FAA** | Federal Aviation Administration (United States Department of Transportation). |
| **Graph-RAG** | Graph-enhanced Retrieval-Augmented Generation combining entity-relationship knowledge graphs with dense vector embeddings. |
| **ISA** | International Standard Atmosphere (ISO 2533:1975), defining standard sea-level conditions ($\rho_0 = 1.225\text{ kg/m}^3$, $T_0 = 288.15\text{ K}$, $P_0 = 101,325\text{ Pa}$) and lapse rates. |
| **KTAS / KCAS** | Knots True Airspeed / Knots Calibrated Airspeed ($1\text{ knot} = 0.514444\text{ m/s}$). |
| **LightRAG** | [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG/blob/main/README.md), dual-level Graph + Vector retrieval framework. |
| **MTOW** | Maximum Takeoff Weight (expressed as mass $m$ in $\text{kg}$ or weight $W = m \cdot g$ in $\text{N}$ or $\text{lbf}$). |
| **Neuro-Symbolic** | Hybrid AI architecture coupling neural networks (for natural language understanding and retrieval) with symbolic/deterministic rule and physics engines (for exact math and logic). |
| **NTRS** | [NASA Technical Reports Server](https://ntrs.nasa.gov/search.jsp?R=19760003955), official repository of NASA scientific and technical aerospace literature. |
| **Part 23** | [14 CFR Part 23](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-23), FAA Airworthiness Standards for Normal, Utility, Acrobatic, and Commuter Category Airplanes ($\le 19$ passengers and MTOW $\le 19,000\text{ lbs}$ / $8,618\text{ kg}$). |
| **Part 25** | [14 CFR Part 25](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-25), FAA Airworthiness Standards for Transport Category Airplanes ($> 19$ passengers or MTOW $> 19,000\text{ lbs}$ / $8,618\text{ kg}$). |
| **SM** | Static Margin, dimensionless measure of longitudinal static stability expressed as a fraction or percentage of Mean Aerodynamic Chord ($\bar{c}$). |
| **V_s0** | Stall speed or minimum steady flight speed in the landing configuration (flaps and landing gear extended). |

### 1.4 References
All regulatory rules, aerodynamic derivations, and software packages integrated into AeroGuard-RAG are grounded in the following primary sources (including the baseline local PDF corpus pre-staged in `data/raw_pdfs/`):

| Reference ID | Document / Repository Title | Author / Standard Body | Canonical URI & Local Corpus Mapping |
| :--- | :--- | :--- | :--- |
| **REF-01** | *IEEE Recommended Practice for Software Requirements Specifications (IEEE Std 830-1998)* | IEEE Computer Society | [IEEE Std 830-1998 Portal](https://standards.ieee.org/standard/830-1998.html) / [PDF Specification](https://seng.cankaya.edu.tr/wp-content/uploads/sites/53/2024/09/IEEE-SRS-830-1998.pdf) |
| **REF-02** | *14 CFR Part 23 — Airworthiness Standards: Normal Category Airplanes* | Federal Aviation Administration (FAA) | [eCFR 14 CFR Part 23](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-23) (`data/raw_pdfs/14 CFR Part 23 (up to date as of 11-09-2026).pdf`) |
| **REF-03** | *14 CFR Part 25 — Airworthiness Standards: Transport Category Airplanes* | Federal Aviation Administration (FAA) | [eCFR 14 CFR Part 25](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-25) (`data/raw_pdfs/14_CFR_Part_25.pdf`) |
| **REF-04** | *Pilot's Handbook of Aeronautical Knowledge (FAA-H-8083-25C)* | Federal Aviation Administration (FAA) | [FAA-H-8083-25 Reference](https://www.sheppardair.com/download/faa-h-8083-25.pdf) & [2025 Addendum](https://asa2fly.com/content/updates/8083-25C_Update.pdf) (`data/raw_pdfs/pilot_handbook.pdf`) |
| **REF-05** | *Introduction to the Aerodynamics of Flight (NASA SP-367 / NTRS 19760003955)* | Theodore A. Talay (NASA Langley Research Center) | [NASA NTRS 19760003955](https://ntrs.nasa.gov/search.jsp?R=19760003955) / [Direct PDF](https://ntrs.nasa.gov/api/citations/19760003955/downloads/19760003955.pdf) (`data/raw_pdfs/19760003955.pdf`) |
| **REF-06** | *Advanced Aerodynamics: Selected NASA Research (NASA CP-2208 / NTRS 19840019592)* | NASA Scientific and Technical Information Branch | [NASA NTRS 19840019592 PDF](https://ntrs.nasa.gov/api/citations/19840019592/downloads/19840019592.pdf) (`data/raw_pdfs/19840019592.pdf`) |
| **REF-07** | *Vortex Flow Aerodynamics, Volume 1 (NASA CP-2416-VOL-1 / NTRS 19860017718)* | J. F. Campbell, R. F. Osborn, J. T. Foughner Jr. (NASA Langley) | [NASA NTRS 19860017718](https://ntrs.nasa.gov/citations/19860017718) / [Direct PDF](https://ntrs.nasa.gov/api/citations/19860017718/downloads/19860017718.pdf) (`data/raw_pdfs/19860017718.pdf`) |
| **REF-08** | *DO-178C: Software Considerations in Airborne Systems and Equipment Certification* | RTCA SC-205 / EUROCAE WG-12 | [RTCA DO-178C Official Portal](https://www.rtca.org/do-178/) |
| **REF-09** | *ARP4754A / ARP4754B: Guidelines for Development of Civil Aircraft and Systems* | SAE International S-18 Committee | [SAE ARP4754 Standard](https://www.sae.org/standards/arp4754b-guidelines-development-civil-aircraft-systems) |
| **REF-10** | *Microsoft MarkItDown & PyMuPDF4LLM Document Parsers* | Microsoft / Artifex Software | [microsoft/markitdown](https://github.com/microsoft/markitdown) & [PyMuPDF4LLM Docs](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) |
| **REF-11** | *HKUDS LightRAG & BAAI BGE-Small-EN-v1.5 Embeddings* | HKU Data Intelligence Lab / BAAI | [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG/blob/main/README.md) & [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) |
| **REF-12** | *AeroSandbox, SymPy, and Pint Scientific Computing Stack* | Peter Sharpe (MIT) / SymPy Team / Hernan Grecco | [peterdsharpe/AeroSandbox](https://github.com/peterdsharpe/AeroSandbox), [sympy/sympy](https://github.com/sympy/sympy), [hgrecco/pint](https://github.com/hgrecco/pint) |

### 1.5 Overview
The remainder of this specification is structured as follows:
* **Section 2 (Overall Description):** Details the system architecture, 5-module relay pipeline, ASCII dataflow diagram, user profiles, local CPU hardware constraints, and global coding standards (`Rules.md`).
* **Section 3 (Specific Requirements — Functional Requirements):** Defines 18 formal functional requirements (`FR-01` through `FR-18`) across Modules A–E and the split-screen UI, specifying exact Input, Processing, and Output contracts.
* **Section 4 (External Interface Requirements):** Specifies the split-screen Streamlit dashboard layout, cloud LLM JSON extraction contracts, and local filesystem/persistence schemas.
* **Section 5 (Non-Functional Requirements):** Establishes strict mathematical determinism guarantees, CPU latency budgets, citation traceability, and fault-handling behaviors.
* **Section 6 (Appendix — Antigravity Implementation & Acceptance Test Suite):** Supplies the complete repository tree, production-ready Pydantic and JSON schemas (`schemas.py`, `schemas_reference.json`, `requirements.txt`), core module implementation blueprints, and 6 automated end-to-end acceptance test cases (`tests/benchmark_prompts.json`).

## 2. Overall Description

### 2.1 Product Perspective
AeroGuard-RAG operates as a standalone, local-first engineering workstation application orchestrated by a deterministic Python state machine (`src/orchestrator.py`). Rather than passing user queries directly to an LLM for unconstrained text generation, the system implements a **5-Module Sequential Relay Pipeline** around a persistent, strongly typed session object (`AircraftDesignState`).

#### 2.1.1 Complete ASCII System Architecture & Relay Flowchart
```text
+====================================================================================================+
|                        OFFLINE STAGE (RUN ONCE PRIOR TO RUNTIME LAUNCH)                            |
+====================================================================================================+
|                                                                                                    |
|  [data/raw_pdfs/*.pdf]                                                                             |
|  - 14 CFR Part 23 (up to date as of 11-09-2026).pdf                                                |
|  - 19760003955.pdf (NASA SP-367)                                                                   |
|  - 19840019592.pdf (NASA CP-2208)                                                                  |
|  - 19860017718.pdf (NASA CP-2416 Vol 1)                                                            |
|  - pilot_handbook.pdf (FAA-H-8083-25C)                                                             |
|         |                                                                                          |
|         v                                                                                          |
|  +----------------------------------------------------------------------------------------------+  |
|  | MODULE A: Offline Knowledge Ingestion Pipeline (src/ingestion/build_index.py)                |  |
|  | 1. SHA-256 manifest delta check (skip already indexed PDFs; incremental update support)      |  |
|  | 2. CPU Layout & Table Extraction via pymupdf4llm + microsoft/markitdown                      |  |
|  | 3. Save clean Markdown + LaTeX equations to data/parsed_markdown/*.md                        |  |
|  | 4. Entity/Relation Graph + Dense Vector Indexing via HKUDS/LightRAG + BAAI/bge-small-en-v1.5 |  |
|  +----------------------------------------------------------------------------------------------+  |
|         |                                                                                          |
|         v                                                                                          |
|  [data/lightrag_storage/]  (Persistent Disk GraphML + NanoVectorDB; loads in < 2.0s at runtime)   |
+====================================================================================================+

                                                 ||
                                                 || (Loaded at App Startup)
                                                 \/

+====================================================================================================+
|                      ONLINE RUNTIME RELAY PIPELINE (Managed by src/orchestrator.py)                |
+====================================================================================================+
|                                                                                                    |
|  [Aerospace Engineer / Student]                                                                    |
|         |                                                                                          |
|         | (Natural Language Design Prompt or Counter-Question Reply)                               |
|         v                                                                                          |
|  +----------------------------------------------------------------------------------------------+  |
|  | STREAMLIT SPLIT-SCREEN UI (app.py)                                                           |  |
|  | Left Panel: Interactive Chat Interface  |  Right Panel: Live Verification & Compliance UI    |  |
|  +----------------------------------------------------------------------------------------------+  |
|         |                                                                ^                         |
|         v                                                                |                         |
|  +--------------------------------------------------------------------+  |                         |
|  | MODULE B: Active Counter-Questioning Gatekeeper                    |  |                         |
|  | (src/gatekeeper/schemas.py & src/gatekeeper/clarifier.py)          |  |                         |
|  | 1. Cloud LLM (Groq Llama-3.3-70B / Gemini-2.5-Flash) extracts      |  |                         |
|  |    structured JSON parameters + raw unit strings into              |  |                         |
|  |    persistent AircraftDesignState (ZERO math performed by LLM).    |  |                         |
|  | 2. Inspects mandatory boundary conditions for detected intent      |  |                         |
|  |    against config/schemas_reference.json.                          |  |                         |
|  +--------------------------------------------------------------------+  |                         |
|         |                                                                |                         |
|         +---> [Missing Mandatory Parameter(s) Detected?]                 |                         |
|         |        |                                                       |                         |
|         |       YES --> [PIPELINE HALTED: Status = HALTED_MISSING_PARAMS]|                         |
|         |               Generates targeted engineering counter-question  |                         |
|         |               (or asks confirmation for ISA sea-level defaults)|                         |
|         |               and returns immediately to Left Chat Panel ------+                         |
|         |                                                                |                         |
|         NO (All Mandatory Parameters Present in AircraftDesignState)     |                         |
|         |                                                                |                         |
|         v                                                                |                         |
|  +--------------------------------------------------------------------+  |                         |
|  | MODULE C: Autonomous Standards & Formula Router                    |  |                         |
|  | (src/retrieval/standards_router.py)                                |  |                         |
|  | 1. Classifies Aircraft Regulatory Category from pax / mass:        |  |                         |
|  |    - <= 19 pax AND <= 8,618 kg (19,000 lbs) -> FAA 14 CFR Part 23  |  |                         |
|  |    - > 19 pax OR > 8,618 kg (19,000 lbs)    -> FAA 14 CFR Part 25  |  |                         |
|  | 2. Queries local LightRAG (hybrid mode) for governing NASA NTRS    |  |                         |
|  |    equations and mandatory FAA airworthiness thresholds.           |  |                         |
|  +--------------------------------------------------------------------+  |                         |
|         |                                                                |                         |
|         v                                                                |                         |
|  +--------------------------------------------------------------------+  |                         |
|  | MODULE D: Deterministic Neuro-Symbolic Physics Solver              |  |                         |
|  | (src/physics_engine/aero_solver.py)                                |  |                         |
|  | 1. Pint UnitRegistry converts all inputs (knots, ft, lbs, etc.)    |  |                         |
|  |    to strict SI base units (m/s, m, m^2, kg, N, Pa, K).            |  |                         |
|  | 2. SymPy validates symbolic equation forms & substitution trace.   |  |                         |
|  | 3. AeroSandbox Atmosphere & Aerodynamics compute exact outputs:    |  |                         |
|  |    rho(h), q, AR, C_L, C_Di, D_i, V_s0, W/S, Static Margin, etc.   |  |                         |
|  +--------------------------------------------------------------------+  |                         |
|         |                                                                |                         |
|         v                                                                |                         |
|  +--------------------------------------------------------------------+  |                         |
|  | MODULE E: Compliance Evaluator & Conditional Design Advisor        |  |                         |
|  | (src/physics_engine/compliance.py)                                 |  |                         |
|  | 1. Evaluates Module D metrics against FAA Part 23/25 & NASA limits.|  |                         |
|  | 2. Assigns Compliance Badge: [PASS] (Green), [WARNING] (Yellow),   |  |                         |
|  |    or [FAIL] (Red).                                                |  |                         |
|  | 3. CONDITIONAL ADVISORY TRIGGER:                                   |  |                         |
|  |    - If PASS: Advisor remains strictly SILENT.                     |  |                         |
|  |    - If WARNING / FAIL: Runs deterministic AeroSandbox parameter   |  |                         |
|  |      sweep (e.g., wingspan b from 1.0*b to 1.30*b in +0.2m steps,  |  |                         |
|  |      or wing area S sweep) to find minimum compliant geometry.     |  |                         |
|  +--------------------------------------------------------------------+  |                         |
|         |                                                                |                         |
|         v                                                                |                         |
|  +--------------------------------------------------------------------+  |                         |
|  | FINAL SYNTHESIS & DASHBOARD DISPATCH (src/orchestrator.py)         |  |                         |
|  | 1. Cloud LLM formats human-readable summary around locked numbers. |  |                         |
|  | 2. Post-generation guardrail verifies zero numeric alteration.     |  |                         |
|  | 3. Updates Left Panel Chat + Right Panel Verification Dashboard ---+--+                         |
+====================================================================================================+
```

### 2.2 Product Functions
1. **Offline PDF-to-Markdown-to-Graph Ingestion (Module A):** Parses multi-column aerospace PDFs (`data/raw_pdfs/`) into structured Markdown with preserved LaTeX equations and pipe tables (`data/parsed_markdown/`), then constructs a persistent local knowledge graph and vector index (`data/lightrag_storage/`).
2. **Stateful Multi-Turn Parameter Gatekeeping (Module B):** Extracts physical quantities and units from conversational turns into `AircraftDesignState`, detects missing boundary conditions per calculation intent, halts execution before any physics call if parameters are incomplete, and issues targeted counter-questions.
3. **Autonomous Regulatory Classification & Citation Retrieval (Module C):** Infers applicable airworthiness standards ([14 CFR Part 23](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-23) vs. [14 CFR Part 25](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-25)) from passenger seating or MTOW without requiring the user to know regulation numbers, and retrieves exact verbatim sections and NASA NTRS equations.
4. **SI-Normalized Symbolic & Numerical Aerodynamic Solving (Module D):** Enforces dimensional consistency via [Pint](https://github.com/hgrecco/pint), builds human-auditable symbolic formula traces via [SymPy](https://github.com/sympy/sympy), and executes deterministic aerodynamic calculations via [AeroSandbox](https://github.com/peterdsharpe/AeroSandbox).
5. **Automated Compliance Grading & Conditional Geometry Optimization (Module E):** Grades every calculated output as `PASS`, `WARNING`, or `FAIL` against regulatory and heuristic limits (`config/schemas_reference.json`), remaining silent on `PASS` and executing a deterministic parameter sweep in AeroSandbox to prescribe exact geometry fixes on `WARNING` or `FAIL`.
6. **Split-Screen Engineering Verification Dashboard (`app.py`):** Renders an interactive chat interface on the left and a live verification audit panel on the right displaying compliance badges, unit conversion tables, symbolic equations, numerical traces, and expandable regulatory citations.

### 2.3 User Characteristics
* **Primary Users:** Aerospace engineering undergraduates, graduate researchers, and preliminary aircraft design engineers who understand aerodynamic fundamentals (lift, drag polar, stall speed, static stability) and require rapid, citation-backed trade studies without writing custom scripts for every query.
* **Secondary Users:** Capstone evaluation faculty and aviation safety auditors reviewing the system's mathematical determinism, regulatory traceability, and immunity to LLM arithmetic hallucinations.

### 2.4 Operating Environment
* **Hardware Target:** Standard consumer laptop or desktop CPU (e.g., Intel Core i5/i7 or AMD Ryzen 5/7, x86_64 or ARM64 architecture, minimum 8 GB RAM, 2 GB free disk space). **Zero local discrete GPU (CUDA/ROCm/Metal) hardware is required.**
* **Operating System:** Cross-platform compatibility across Windows 10/11 (PowerShell / Command Prompt), Ubuntu Linux 22.04+, and macOS 13+.
* **Runtime Environment:** Python 3.10+ virtual environment (`.venv`) executing locally, with outbound HTTPS required only for lightweight free-tier LLM JSON extraction/formatting calls (`api.groq.com` or `generativelanguage.googleapis.com`).

### 2.5 Design and Implementation Constraints

#### 2.5.1 Mandatory Global Coding Standards (`Rules.md`)
All code generated by Google Antigravity for this repository must strictly obey the project's global engineering rules defined in `Rules.md`:
1. **YAGNI (You Aren't Gonna Need It):** Do not build speculative abstractions, unused base classes, or unrequested features until needed by this specification.
2. **Fail Fast:** Raise explicit, typed exceptions (`ValueError`, `pint.DimensionalityError`, `pydantic.ValidationError`, `RuntimeError`) immediately when invalid states or unit mismatches occur rather than masking errors with silent fallbacks.
3. **Simple First:** Implement direct, transparent, deterministic algorithms first; add complexity only where mandated by the 5-module relay architecture.
4. **Delete Aggressively:** Minimize boilerplate and dead code (`less code = fewer bugs`).
5. **Semantic Naming:** Always name variables, function parameters, class attributes, and internal endpoints with verbose, self-documenting engineering names (e.g., `wingspan_meters`, `cruise_true_airspeed_meters_per_second`, `induced_drag_coefficient_cdi`, `maximum_takeoff_mass_kilograms`) rather than cryptic single-letter variables (`b`, `v`, `c`, `m`) in Python application logic.

#### 2.5.2 Hardware, Cost & Architectural Constraints
* **Zero Local GPU Constraint (`CON-01`):** Local embedding generation (`BAAI/bge-small-en-v1.5` via `sentence-transformers` or `onnxruntime` on CPU) and physics solving (`AeroSandbox` + `NumPy` + `CasADi` + `SymPy`) must run 100% on CPU threads (`device="cpu"`).
* **Zero-Cost API Stack (`CON-02`):** Cloud LLM calls must use free-tier API keys loaded via `python-dotenv` from `.env` (`GROQ_API_KEY` for `llama-3.3-70b-versatile` as primary, or `GEMINI_API_KEY` for `gemini-2.5-flash` as fallback).
* **Strict Zero-LLM-Math Constraint (`CON-03`):** The LLM is strictly forbidden from computing aerodynamic formulas, performing unit conversions, or rounding/modifying verified solver outputs. Every floating-point engineering output displayed to the user must originate exclusively from `src/physics_engine/aero_solver.py` or `src/physics_engine/compliance.py`.
* **Offline-First Persistence (`CON-04`):** `app.py` must never re-parse or re-embed PDFs during user chat sessions. It must load the pre-built `data/lightrag_storage/` directory from disk in $\le 2.0\text{ seconds}$.

### 2.6 Assumptions and Dependencies
* **Pre-Staged Regulatory & Technical Corpus:** Assumes the raw PDF corpus (including `14 CFR Part 23 (up to date as of 11-09-2026).pdf`, `19760003955.pdf`, `19840019592.pdf`, `19860017718.pdf`, and `pilot_handbook.pdf`) is placed in `data/raw_pdfs/` prior to running `python -m src.ingestion.build_index`.
* **Deterministic Threshold Fallback:** While `LightRAG` retrieves rich regulatory context and explanations from the indexed corpus, `config/schemas_reference.json` acts as the authoritative, machine-verifiable lookup table for exact numerical regulatory boundaries (e.g., $V_{s0} \le 61.0\text{ knots}$) so compliance grading remains 100% deterministic even if a text chunk is partially truncated.

## 3. Specific Requirements — Functional Requirements

Each functional requirement (`FR-01` through `FR-18`) is specified with explicit **Input**, **Processing**, and **Output** engineering contracts for autonomous implementation.

### 3.1 Module A: Offline Knowledge Ingestion Pipeline (`src/ingestion/build_index.py`)

#### FR-01: Multi-Column PDF-to-Markdown Conversion with Formula Preservation
* **Input:** Raw PDF files located in `data/raw_pdfs/*.pdf` (specifically including [14 CFR Part 23](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-23), [NASA SP-367 / 19760003955](https://ntrs.nasa.gov/search.jsp?R=19760003955), [NASA CP-2208 / 19840019592](https://ntrs.nasa.gov/api/citations/19840019592/downloads/19840019592.pdf), [NASA CP-2416 / 19860017718](https://ntrs.nasa.gov/citations/19860017718), and [FAA-H-8083-25C](https://www.sheppardair.com/download/faa-h-8083-25.pdf)).
* **Processing:**
  1. Iterate over all `.pdf` files in `data/raw_pdfs/`.
  2. Extract layout-aware Markdown and multi-column tables on CPU using `pymupdf4llm.to_markdown(pdf_path, write_images=False)` as the primary layout parser, coupled with `markitdown.MarkItDown()` normalization to preserve section headers, regulatory paragraph markers (e.g., `§ 23.2110`, `§ 23.49`), and inline/block LaTeX equations.
  3. Inject standardized YAML frontmatter at the top of each generated Markdown file recording `source_pdf_filename`, `sha256_checksum`, `ingestion_timestamp_utc`, and `document_authority` (`FAA` or `NASA_NTRS`).
* **Output:** Clean UTF-8 Markdown files written to `data/parsed_markdown/<stem>.md`.

#### FR-02: Hybrid Knowledge Graph & Dense Vector Indexing via LightRAG
* **Input:** Parsed Markdown documents in `data/parsed_markdown/*.md`.
* **Processing:**
  1. Initialize `LightRAG(working_dir="data/lightrag_storage", embedding_func=bge_small_cpu_embed, llm_model_func=cloud_llm_complete)` where `bge_small_cpu_embed` wraps [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) (384-dimensional embeddings) running strictly on CPU (`device="cpu"`).
  2. Chunk documents using structural Markdown header boundaries (`chunk_token_size=800`, `chunk_overlap_token_size=100`) so tables and equations are never split mid-block.
  3. Extract aerodynamic domain entities (`Aerodynamic_Parameter`, `Equation`, `Regulation_Section`, `Aircraft_Category`, `Threshold_Limit`) and relationships into the local NetworkX/GraphML store and NanoVectorDB files.
* **Output:** Populated persistent storage files inside `data/lightrag_storage/` (`graph_chunk_entity_relation.graphml`, `vdb_entities.json`, `vdb_relationships.json`, `vdb_chunks.json`, `kv_store_full_docs.json`, and `kv_store_text_chunks.json`).

#### FR-03: Incremental Checksum Manifest & Idempotent Re-Indexing
* **Input:** Directory contents of `data/raw_pdfs/` and `data/lightrag_storage/ingestion_manifest.json`.
* **Processing:**
  1. Compute the SHA-256 hash of each PDF in `data/raw_pdfs/`.
  2. Compare against `data/lightrag_storage/ingestion_manifest.json`.
  3. Skip any PDF whose SHA-256 hash already exists in the manifest; process and insert only newly added or modified PDFs into `LightRAG`, then atomic-write the updated manifest.
* **Output:** Updated `data/lightrag_storage/ingestion_manifest.json` and console telemetry reporting `files_skipped_count` and `files_indexed_count`.

### 3.2 Module B: Active Counter-Questioning Gatekeeper (`src/gatekeeper/schemas.py` & `clarifier.py`)

#### FR-04: Structured Intent & Parameter Extraction with Raw Unit Capture
* **Input:** User natural-language message string `user_query_text` and current session `AircraftDesignState`.
* **Processing:**
  1. Prompt the configured Cloud LLM (`llama-3.3-70b-versatile` or `gemini-2.5-flash`) with `temperature=0.0` and `response_format={"type": "json_object"}` using a strict extraction system prompt.
  2. Identify the primary `calculation_intent` from the supported enum: `["induced_drag", "stall_speed", "wing_loading", "climb_gradient", "static_margin", "breguet_range", "compressibility_correction", "full_aerodynamic_audit", "out_of_scope"]`.
  3. Extract any explicitly stated numerical values and their exact raw unit strings (e.g., `{"value": 110.0, "unit": "knots"}`, `{"value": 36.0, "unit": "ft"}`) without performing any arithmetic or unit conversion inside the LLM.
  4. Detect if the user explicitly confirmed standard assumptions (e.g., *"Yes, assume standard ISA sea-level conditions"* $\rightarrow$ sets `altitude_meters = 0.0`, `oswald_efficiency_factor = 0.80`, `maximum_lift_coefficient_clmax = 1.50`).
* **Output:** Validated `ExtractedTurnParameters` Pydantic object containing extracted fields and `calculation_intent`.

#### FR-05: Multi-Turn State Merging & Passenger-Mass Heuristic Resolution
* **Input:** Current `AircraftDesignState` instance and `ExtractedTurnParameters` from the latest turn.
* **Processing:**
  1. Non-destructively merge all non-`None` fields from `ExtractedTurnParameters` into `AircraftDesignState`, preserving all previously supplied parameters from earlier turns unless explicitly overridden by the user.
  2. If `aircraft_mass_kilograms` is `None` but `passenger_count` is provided (and the user has not provided an explicit empty/gross weight), apply the standard preliminary design mass estimation rule defined in `config/schemas_reference.json` ONLY when `allow_pax_mass_heuristic` is enabled or confirmed, OR keep `aircraft_mass_kilograms` as a required parameter while recording `passenger_count` for regulatory category routing. Specifically, if the user provides only `passenger_count` without gross aircraft mass/weight, record `passenger_count` for Part 23/25 routing and flag `aircraft_mass_kilograms` as missing unless the user provides total mass/weight or confirms standard per-passenger gross mass scaling ($100\text{ kg/pax}$ payload + airframe mass fraction $\rightarrow 450\text{ kg/pax}$ total gross mass baseline for GA/commuter aircraft).
* **Output:** Updated `AircraftDesignState` with incremented `turn_index` and audit log of updated fields.

#### FR-06: Mandatory Boundary-Condition Inspection & Relay Pipeline Halt
* **Input:** Updated `AircraftDesignState` and `config/schemas_reference.json` intent-to-parameter mapping.
* **Processing:**
  1. Look up the list of `mandatory_parameters` for `state.calculation_intent` in `config/schemas_reference.json` (e.g., for `induced_drag`: `["wingspan", "wing_area", "aircraft_mass", "true_airspeed", "altitude"]`; for `stall_speed`: `["wing_area", "aircraft_mass", "altitude", "maximum_lift_coefficient_clmax"]`).
  2. Check each mandatory attribute in `AircraftDesignState`.
  3. If one or more mandatory attributes are `None`, immediately set `state.pipeline_status = "HALTED_MISSING_PARAMS"` and list the missing attribute keys in `state.missing_parameters`.
  4. Prevent `orchestrator.py` from invoking Module C, Module D, or Module E while `state.pipeline_status == "HALTED_MISSING_PARAMS"`.
* **Output:** Boolean gate decision (`is_ready_for_physics: bool`) and populated `state.missing_parameters` list.

#### FR-07: Targeted Engineering Counter-Question Generation
* **Input:** `AircraftDesignState` with non-empty `missing_parameters` list.
* **Processing:**
  1. Construct a deterministic, concise engineering counter-question listing every missing boundary condition with its expected physical dimension and example units (e.g., *"To compute the induced drag without guessing boundary conditions, please provide the following missing parameters: 1. **Wing Planform Area ($S$)** (e.g., $\text{m}^2$ or $\text{ft}^2$), 2. **Aircraft Gross Mass ($m$)** (e.g., $\text{kg}$ or $\text{lbs}$), 3. **True Airspeed ($V_\infty$)** (e.g., $\text{knots}$ or $\text{m/s}$), and 4. **Cruise Altitude ($h$)** (or reply **'use ISA sea-level defaults'** to assume $h = 0\text{ m}$ and Oswald efficiency $e = 0.80$)."*).
* **Output:** Counter-question string returned to the Streamlit chat interface and logged in `state.conversation_history`.

### 3.3 Module C: Autonomous Standards & Formula Router (`src/retrieval/standards_router.py`)

#### FR-08: Autonomous FAA 14 CFR Part 23 vs. Part 25 Category Classifier
* **Input:** `AircraftDesignState` containing `passenger_count` and/or SI-normalized `aircraft_mass_kilograms`.
* **Processing:**
  1. Evaluate deterministic classification rules per [14 CFR § 23.2005](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-23) and [14 CFR § 25.1](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-25/subpart-A):
     * If (`passenger_count` is `None` or `passenger_count <= 19`) **AND** (`aircraft_mass_kilograms <= 8618.255` [19,000 lbs]): classify as `FAA_14_CFR_PART_23` (Sub-level: Level 1 for 0–1 pax, Level 2 for 2–6 pax, Level 3 for 7–9 pax, Level 4 / Commuter for 10–19 pax).
     * If (`passenger_count > 19`) **OR** (`aircraft_mass_kilograms > 8618.255` [19,000 lbs]): classify as `FAA_14_CFR_PART_25` (Transport Category Airplane).
  2. Bind the corresponding regulatory constraint profile from `config/schemas_reference.json` to `state.regulatory_category`.
* **Output:** Populated `state.regulatory_category`, `state.certification_level`, and active threshold dictionary.

#### FR-09: Hybrid LightRAG Retrieval of Governing Equations & Regulatory Citations
* **Input:** `state.calculation_intent`, `state.regulatory_category`, and pre-loaded `LightRAG` instance from `data/lightrag_storage/`.
* **Processing:**
  1. Formulate a targeted domain query combining the calculation intent and regulatory category (e.g., `"FAA 14 CFR Part 23 stall speed Vs0 61 knots limit and NASA SP-367 19760003955 lift induced drag aspect ratio equations"`).
  2. Query `LightRAG` using `QueryParam(mode="hybrid", top_k=5, only_need_context=True)` to retrieve both knowledge-graph entity relationships and verbatim Markdown document chunks without triggering an extra generative LLM call inside LightRAG.
  3. Parse retrieved chunks to extract `source_pdf_filename`, section/report identifiers, and verbatim excerpt snippets.
  4. If the query domain is outside the indexed aerodynamics/airworthiness corpus (`calculation_intent == "out_of_scope"` or maximum vector similarity $< 0.55$), flag `RetrievalCoverageError` for graceful out-of-scope handling.
* **Output:** List of `RegulatoryCitation` objects attached to `state.retrieved_citations`.

### 3.4 Module D: Deterministic Neuro-Symbolic Physics Solver (`src/physics_engine/aero_solver.py`)

#### FR-10: Strict SI Unit Normalization & Dimensional Analysis via Pint
* **Input:** Raw parameter values and unit strings stored in `AircraftDesignState` (e.g., `wingspan = (36.0, "ft")`, `true_airspeed = (110.0, "knots")`, `aircraft_mass = (2400.0, "lbs")`, `altitude = (5000.0, "ft")`).
* **Processing:**
  1. Instantiate a singleton `pint.UnitRegistry()`.
  2. Parse every input quantity `ureg.Quantity(value, unit_str)`.
  3. Validate physical dimensionality against expected SI dimensions (Length `[L]`, Area `[L]^2`, Mass `[M]` or Force `[M]*[L]/[T]^2`, Velocity `[L]/[T]`). If a user passes a force unit (`lbf` or `N`) for aircraft weight, convert to mass via $m = W / g_0$ where $g_0 = 9.80665\text{ m/s}^2$. If incompatible dimensions are supplied (e.g., `knots` for `wingspan`), raise `pint.DimensionalityError` immediately (obeying `Rules.md` **fail fast**).
  4. Convert all quantities to strict SI base units (`meters`, `meters**2`, `kilograms`, `meters/second`, `kelvin`, `pascal`, `newtons`) and record both the original input representation and the exact SI converted float in `UnitConversionRecord`.
* **Output:** Dictionary of SI-normalized floats and list of `UnitConversionRecord` entries stored in `state.unit_conversions`.

#### FR-11: ISA Atmosphere & Subsonic/Compressible Aerodynamic Solver via AeroSandbox & SymPy
* **Input:** SI-normalized boundary conditions from `FR-10`.
* **Processing:**
  1. **Atmospheric State (`AeroSandbox`):** Instantiate `asb.Atmosphere(altitude=altitude_meters)` to compute exact ISA atmospheric density $\rho(h)$ ($\text{kg/m}^3$), static pressure $P(h)$ ($\text{Pa}$), temperature $T(h)$ ($\text{K}$), speed of sound $a(h)$ ($\text{m/s}$), and dynamic viscosity $\mu(h)$ ($\text{Pa}\cdot\text{s}$).
  2. **Symbolic Trace Construction (`SymPy`):** Define symbolic expressions and LaTeX representations for every active equation so the UI can display both the symbolic formula and the exact substituted numbers:
     * Weight: $W = m \cdot g_0$ (with $g_0 = 9.80665\text{ m/s}^2$)
     * Dynamic Pressure: $q_\infty = \frac{1}{2} \rho V_\infty^2$
     * Aspect Ratio: $AR = \frac{b^2}{S}$
     * Wing Loading: $\frac{W}{S} = \frac{m \cdot g_0}{S}$ ($\text{N/m}^2$) and mass wing loading $\frac{m}{S}$ ($\text{kg/m}^2$)
     * Lift Coefficient (Steady Level Flight $L = W$): $C_L = \frac{W}{q_\infty \cdot S} = \frac{2 W}{\rho V_\infty^2 S}$
     * Induced Drag Coefficient: $C_{Di} = \frac{C_L^2}{\pi \cdot AR \cdot e}$ (default $e = 0.80$ if not overridden)
     * Induced Drag Force: $D_i = q_\infty \cdot S \cdot C_{Di}$
     * Total Drag & Lift-to-Drag Ratio (when $C_{D0}$ is known, default $C_{D0} = 0.025$): $C_D = C_{D0} + C_{Di}$, $D = q_\infty \cdot S \cdot C_D$, $(L/D) = C_L / C_D$
     * Power-Off Stall Speed ($V_{s0}$): $V_{s0} = \sqrt{\frac{2 W}{\rho \cdot S \cdot C_{L,\max}}}$ (converted to both $\text{m/s}$ and $\text{knots}$)
     * Mach Number & Prandtl-Glauert Correction: $M_\infty = \frac{V_\infty}{a(h)}$, and for $0.30 \le M_\infty < 0.85$, $C_{p,\text{comp}} = \frac{C_{p,0}}{\sqrt{1 - M_\infty^2}}$
     * Reynolds Number: $Re = \frac{\rho V_\infty \bar{c}}{\mu}$ where $\bar{c} = S / b$
     * Static Longitudinal Stability (when $x_{cg}, x_{np}, \bar{c}$ provided): $SM = \frac{x_{np} - x_{cg}}{\bar{c}}$
     * Steady Climb Gradient (when available thrust $T_{\text{avail}}$ provided): $\sin\gamma = \frac{T_{\text{avail}} - D}{W}$, $\text{CGR (\%)} = 100 \cdot \tan(\arcsin(\sin\gamma))$
     * Breguet Range (when propeller efficiency $\eta_p$, specific fuel consumption $c_p$, and fuel mass $m_f$ provided): $R = \frac{\eta_p}{c_p} \frac{C_L}{C_D} \ln\left(\frac{W_i}{W_f}\right)$
  3. Execute numerical evaluation in IEEE 754 double precision (`float64`) and cross-verify that `SymPy.subs()` evaluation matches the `AeroSandbox`/`NumPy` float evaluation to within $10^{-9}$ relative tolerance.
* **Output:** Populated `PhysicsSolutionBundle` containing all computed SI metrics, secondary Aviation unit metrics (e.g., $V_{s0}$ in knots), and step-by-step `EquationTrace` objects.

### 3.5 Module E: Compliance Evaluator & Conditional Design Advisor (`src/physics_engine/compliance.py`)

#### FR-12: Deterministic Regulatory & Heuristic Threshold Evaluation
* **Input:** `PhysicsSolutionBundle` from Module D, `state.regulatory_category` from Module C, and threshold rules from `config/schemas_reference.json`.
* **Processing:**
  1. Compare each computed metric against its applicable regulatory and engineering boundaries:
     * **FAA Part 23 Single-Engine / Certified Landing Stall Speed Rule ([14 CFR § 23.2110](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-23) / Historic § 23.49):**
       * `PASS`: $V_{s0} \le 58.0\text{ knots}$ ($29.838\text{ m/s}$) — healthy safety margin below the 61-knot maximum limit.
       * `WARNING`: $58.0\text{ knots} < V_{s0} \le 61.0\text{ knots}$ ($31.381\text{ m/s}$) — within legal certification limit but within $5\%$ of the hard regulatory ceiling.
       * `FAIL`: $V_{s0} > 61.0\text{ knots}$ ($31.381\text{ m/s}$) — violates FAA Part 23 single-engine / commuter landing stall speed limit without specialized crashworthiness compensating approval.
     * **Induced Drag & Aspect Ratio Efficiency Heuristic ([NASA SP-367 / NTRS 19760003955](https://ntrs.nasa.gov/search.jsp?R=19760003955)):**
       * `PASS`: $C_{Di} \le 0.040$ and $AR \ge 6.5$.
       * `WARNING`: $0.040 < C_{Di} \le 0.065$ or $5.0 \le AR < 6.5$.
       * `FAIL`: $C_{Di} > 0.065$ or $AR < 5.0$ (for non-delta subsonic transport/utility aircraft).
     * **Static Longitudinal Stability Margin Rule ([14 CFR § 23.2135](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-23) / [14 CFR § 25.173](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-25)):**
       * `PASS`: $+0.05 \le SM \le +0.25$ ($5\%$ to $25\%$ MAC positive static stability).
       * `WARNING`: $+0.02 \le SM < +0.05$ or $+0.25 < SM \le +0.35$.
       * `FAIL`: $SM < +0.02$ (statically unstable / neutrally unstable pitch divergence risk) or $SM > +0.35$ (excessive elevator trim drag).
     * **Steady Climb Gradient Rule ([14 CFR § 23.2120](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-23)):**
       * `PASS`: Climb gradient $\ge 8.3\%$ (Part 23 low-speed single-engine balked landing / takeoff climb requirement: $1:12$ gradient $= 8.33\%$).
       * `WARNING`: $6.0\% \le \text{Climb Gradient} < 8.3\%$.
       * `FAIL`: $\text{Climb Gradient} < 6.0\%$.
  2. Aggregate individual rule checks into an overall turn badge using worst-case precedence: `FAIL` $>$ `WARNING` $>$ `PASS`.
* **Output:** `ComplianceReport` containing overall status (`PASS`, `WARNING`, or `FAIL`), individual `RuleCheckResult` items, and exact delta margins.

#### FR-13: Silent Advisor Enforcement on Healthy Designs (`PASS`)
* **Input:** `ComplianceReport` from `FR-12`.
* **Processing:**
  1. Check if `ComplianceReport.overall_status == "PASS"`.
  2. If `PASS`, bypass the parametric sweep optimizer completely and set `ComplianceReport.design_advisory = None`. The system must not clutter the engineer's workflow with unsolicited redesign advice when all regulatory and efficiency criteria are satisfied cleanly.
* **Output:** `design_advisory = None` and execution time of $0.0\text{ ms}$ for the advisory step.

#### FR-14: Conditional AeroSandbox Parameter-Sweep Advisor on `WARNING` or `FAIL`
* **Input:** `ComplianceReport` with `overall_status in ("WARNING", "FAIL")` and SI-normalized `AircraftDesignState`.
* **Processing:**
  1. Identify the violated metric(s):
     * **Case 1 — Induced Drag / Aspect Ratio Violation ($C_{Di}$ too high or $AR$ too low):** Run a deterministic parameter sweep in `AeroSandbox` iterating candidate wingspan $b_{\text{cand}}$ from $1.00 \cdot b_0$ up to $1.30 \cdot b_0$ in $+0.20\text{ m}$ increments (and up to $1.60 \cdot b_0$ if $+30\%$ is still insufficient, while reporting both the $+30\%$ sweep ceiling result and the exact minimum compliant span) at constant wing area $S_0$ (or constant mean geometric chord) to compute $AR(b_{\text{cand}})$, $C_{Di}(b_{\text{cand}})$, and $D_i(b_{\text{cand}})$. Select the first $b_{\text{cand}}$ where $C_{Di} \le C_{Di,\text{target}}$ ($0.040$).
     * **Case 2 — Stall Speed Violation ($V_{s0} > 61.0\text{ knots}$):** Since $V_{s0} = \sqrt{\frac{2 W}{\rho S C_{L,\max}}}$, keeping chord constant while increasing wingspan $b_{\text{cand}}$ from $1.00 \cdot b_0$ up to $1.30 \cdot b_0$ in $+0.20\text{ m}$ increments (where $S_{\text{cand}} = b_{\text{cand}} \cdot \bar{c}_0$) AND/OR sweeping wing planform area $S_{\text{cand}}$ in $+0.50\text{ m}^2$ increments and high-lift flap $C_{L,\max}$ from $C_{L,\max,0}$ up to $2.20$ in $+0.05$ increments, identify the exact minimum geometry modification ($\Delta b$, $\Delta S$, or required $C_{L,\max}$) needed to bring $V_{s0} \le 61.0\text{ knots}$ (for `FAIL` recovery) and $V_{s0} \le 58.0\text{ knots}$ (for full `PASS` margin).
     * **Case 3 — Static Margin Violation ($SM < 0.05$):** Compute the exact forward CG shift $\Delta x_{cg} = x_{cg} - (x_{np} - 0.05 \cdot \bar{c})$ in meters and `% MAC` required to restore a $+5.0\%$ static margin.
  2. Package the sweep trajectory and exact minimum compliant geometry delta into a structured `DesignAdvisory` object.
* **Output:** Populated `DesignAdvisory` containing `parameter_swept`, `original_value_si`, `recommended_value_si`, `percentage_change`, `projected_metric_value`, and the sweep table rows.

### 3.6 Orchestrator & Split-Screen Streamlit UI (`src/orchestrator.py` & `app.py`)

#### FR-15: Central Relay Controller & Post-Generation Numeric Guardrail
* **Input:** User prompt string and `st.session_state.aircraft_design_state`.
* **Processing:**
  1. Execute Module B (`clarifier.py`). If `HALTED_MISSING_PARAMS`, return counter-question immediately.
  2. Otherwise, execute Module C (`standards_router.py`) $\rightarrow$ Module D (`aero_solver.py`) $\rightarrow$ Module E (`compliance.py`).
  3. Pass the verified `PhysicsSolutionBundle` and `ComplianceReport` to the Cloud LLM strictly to compose a concise narrative summary around the locked numbers.
  4. **Post-Generation Numeric Guardrail:** Verify programmatically that the key primary output numbers present in `PhysicsSolutionBundle` appear unaltered in the response card, and bind the right-hand Verification Dashboard directly to the deterministic Python objects (`PhysicsSolutionBundle`, `ComplianceReport`, `retrieved_citations`)—never to LLM-generated text.
* **Output:** Turn response payload containing `assistant_chat_markdown` and deterministic `VerificationDashboardPayload`.

#### FR-16: Left Panel — Conversational Engineering Chat Interface
* **Input:** `state.conversation_history` and user text input via `st.chat_input`.
* **Processing:**
  1. Render full multi-turn conversation history with role avatars (`user` vs. `assistant`).
  2. Display a compact pill bar above the chat input showing currently locked parameters in `AircraftDesignState` (e.g., `b = 10.97 m | S = 16.17 m² | m = 1,111.3 kg | V = 56.59 m/s | h = 0 m | Cat: Part 23`) and a **"Reset Design Session"** button.
* **Output:** Interactive left column in `app.py`.

#### FR-17: Right Panel — Live Compliance Badge & Deterministic Math Trace
* **Input:** Latest `VerificationDashboardPayload` stored in `st.session_state`.
* **Processing:**
  1. Render top-level **Compliance Status Banner** with color-coded styling:
     * `PASS`: Emerald Green (`#16A34A`) badge — *"COMPLIANT — ALL FAA & NASA CRITERIA SATISFIED"*
     * `WARNING`: Amber Yellow (`#D97706`) badge — *"MARGINAL COMPLIANCE — NEAR REGULATORY THRESHOLD"*
     * `FAIL`: Crimson Red (`#DC2626`) badge — *"NON-COMPLIANT — REGULATORY OR AERODYNAMIC LIMIT EXCEEDED"*
     * `AWAITING_PARAMETERS`: Slate Blue (`#2563EB`) badge — *"GATEKEEPER ACTIVE — AWAITING BOUNDARY CONDITIONS"*
  2. Render **Unit Normalization Table** (`Input Parameter`, `User Value & Unit`, `SI Normalized Value & Unit`).
  3. Render **Symbolic & Substituted Equation Trace** using `st.latex()` for each step in `PhysicsSolutionBundle.equation_traces`.
  4. If `ComplianceReport.design_advisory` is present (`WARNING` or `FAIL`), render the **AeroSandbox Parametric Sweep Advisory Card** highlighting the exact required geometry change ($\Delta b$ or $\Delta S$) and a compact sweep table.
* **Output:** Live-updating right verification panel in `app.py`.

#### FR-18: Right Panel — Expandable Verbatim NASA/FAA Source Citations
* **Input:** `state.retrieved_citations` from Module C.
* **Processing:**
  1. Render an expandable `st.expander()` card per citation displaying the source document badge (`[FAA 14 CFR Part 23]`, `[NASA SP-367 / 19760003955]`, etc.), section/page reference, and verbatim Markdown/LaTeX excerpt from `data/parsed_markdown/`.
* **Output:** Auditable citation drawers in the bottom section of the right verification panel.

## 4. External Interface Requirements

### 4.1 User Interface Split-Screen Specification (`app.py`)
The Streamlit application (`app.py`) must configure `st.set_page_config(page_title="AeroGuard-RAG | Neuro-Symbolic Aerospace Assistant", layout="wide")` and enforce a `50% / 50%` two-column split (`left_chat_col, right_verify_col = st.columns([1, 1], gap="large")`):

| UI Region | Component ID | Visual & Functional Specification |
| :--- | :--- | :--- |
| **Top Header Bar** | `header_bar` | Displays system title, active LLM provider status (`Groq llama-3.3-70b-versatile` or `Gemini 2.5 Flash`), local LightRAG index status (`READY — 5 Corpus Docs Indexed`), and a `"Reset Session State"` button. |
| **Left Column (Top)** | `active_state_pills` | Displays current `AircraftDesignState` variables in a horizontal metric strip (`Wingspan b`, `Wing Area S`, `Gross Mass m`, `Airspeed V`, `Altitude h`, `Category`). Missing required fields show `MISSING (None)`. |
| **Left Column (Main)** | `chat_container` | Scrollable `st.container(height=620)` rendering `st.chat_message("user")` and `st.chat_message("assistant")` turns, pinned above `st.chat_input("Describe your aircraft geometry, flight condition, or reply to counter-questions...")`. |
| **Right Column (Card 1)** | `compliance_badge_card` | Renders HTML/CSS status banner (`PASS` `#16A34A`, `WARNING` `#D97706`, `FAIL` `#DC2626`, or `HALTED_MISSING_PARAMS` `#2563EB`) with active regulatory standard (`FAA 14 CFR Part 23` or `Part 25`). |
| **Right Column (Card 2)** | `deterministic_math_card` | Displays: (1) Pint SI Unit Conversion Markdown table, (2) `st.latex()` symbolic formula + substituted numerical trace, and (3) Final verified metrics table (`AR`, `C_L`, `C_Di`, `D_i [N]`, `V_s0 [knots]`, `W/S [N/m²]`). |
| **Right Column (Card 3)** | `conditional_advisor_card` | Hidden when `overall_status == "PASS"`. Visible only on `WARNING` or `FAIL`, displaying the AeroSandbox parameter sweep recommendation and sweep progression table. |
| **Right Column (Card 4)** | `regulatory_citations_card` | Renders `st.expander()` accordions for each retrieved NASA NTRS / FAA CFR chunk with source filename, SHA-256 verification tag, and verbatim text/LaTeX equations. |

### 4.2 Software & Cloud API Interfaces

| Interface Name | Library / Endpoint | Version / Model | Interface Contract & Constraint |
| :--- | :--- | :--- | :--- |
| **Primary Cloud LLM** | [Groq Cloud API](https://console.groq.com/) (`groq` Python SDK) | `llama-3.3-70b-versatile` | Authenticated via `GROQ_API_KEY` in `.env`. Invoked with `temperature=0.0` and `response_format={"type": "json_object"}` for Module B parameter extraction, and `temperature=0.1` for final narrative summary formatting. |
| **Fallback Cloud LLM** | [Google AI Studio API](https://aistudio.google.com/) (`google-genai` SDK) | `gemini-2.5-flash` | Authenticated via `GEMINI_API_KEY` in `.env`. Automatically used if `GROQ_API_KEY` is absent or returns HTTP `429` rate limit. |
| **Local Embedding Engine** | [Hugging Face Sentence-Transformers](https://huggingface.co/BAAI/bge-small-en-v1.5) | `BAAI/bge-small-en-v1.5` | Loaded locally with `device="cpu"`, `normalize_embeddings=True`, embedding dimension `384`. Zero external API cost. |
| **Graph-RAG Engine** | [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG/blob/main/README.md) | `lightrag-hku >= 1.0.6` | Configured with local storage directory `data/lightrag_storage/` and `QueryParam(mode="hybrid", only_need_context=True)` during runtime queries. |
| **PDF Parsing Engine** | [Microsoft MarkItDown](https://github.com/microsoft/markitdown) & [PyMuPDF4LLM](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) | `markitdown >= 0.0.1a3`, `pymupdf4llm >= 0.0.17` | Used exclusively in `src/ingestion/build_index.py` to extract Markdown tables and LaTeX blocks from `data/raw_pdfs/`. |
| **Aerodynamic Physics Engine** | [AeroSandbox](https://github.com/peterdsharpe/AeroSandbox) | `aerosandbox >= 4.2.4` | Executes ISA atmospheric state (`asb.Atmosphere`) and vectorized parameter sweeps on CPU. |
| **Symbolic & Unit Engine** | [SymPy](https://github.com/sympy/sympy) & [Pint](https://github.com/hgrecco/pint) | `sympy >= 1.13.0`, `pint >= 0.24` | `pint.UnitRegistry` enforces SI conversion; `sympy` generates symbolic LaTeX equations and verifies numerical substitution. |

### 4.3 Local File System & Persistence Interfaces
* **`data/raw_pdfs/`:** Read-only directory containing raw source PDFs (`14 CFR Part 23 (up to date as of 11-09-2026).pdf`, `19760003955.pdf`, `19840019592.pdf`, `19860017718.pdf`, `pilot_handbook.pdf`, plus any additional FAA Part 25 / NASA reports).
* **`data/parsed_markdown/`:** Stores intermediate UTF-8 `.md` files generated during offline ingestion for human inspection and verbatim citation rendering.
* **`data/lightrag_storage/`:** Stores persistent GraphML, vector index JSONs, and `ingestion_manifest.json`.
* **`config/schemas_reference.json`:** Read-only deterministic JSON configuration storing mandatory parameters per intent, regulatory classification thresholds, and compliance rule limits.
* **`tests/benchmark_prompts.json`:** Automated regression and acceptance test definitions executed by `pytest`.

## 5. Non-Functional Requirements

### 5.1 Determinism & Zero-Math-Hallucination Guarantee (`NFR-01`)
* **Bitwise Reproducibility:** Given identical numerical inputs in `AircraftDesignState`, Modules D and E must produce identical IEEE 754 `float64` outputs across $1,000$ consecutive runs ($\sigma^2 = 0.0$).
* **Hard LLM Firewall:** No prompt sent to Groq or Gemini may request arithmetic evaluation, unit conversion, or threshold comparison. Every number displayed in the Right Verification Dashboard must be rendered directly from Python `float` fields in `PhysicsSolutionBundle` and `ComplianceReport`.

### 5.2 Performance & CPU Latency Targets (`NFR-02`)
On a standard consumer laptop CPU (Intel Core i5 / Ryzen 5, 8 GB RAM, zero GPU):
1. **Runtime Cold-Start Index Load:** Loading `data/lightrag_storage/` into memory at `app.py` startup must complete in $\le 2.0\text{ seconds}$.
2. **Gatekeeper Counter-Question Turn Latency:** Turns that halt at Module B (`HALTED_MISSING_PARAMS`) must complete in $\le 1.5\text{ seconds}$ (single lightweight JSON extraction call + deterministic schema check).
3. **Full Neuro-Symbolic Relay Turn Latency:** Complete end-to-end execution across Module B $\rightarrow$ Module C (LightRAG hybrid retrieval) $\rightarrow$ Module D (Pint + SymPy + AeroSandbox solver) $\rightarrow$ Module E (Compliance check + 30-step AeroSandbox wingspan sweep) $\rightarrow$ UI render must complete in $\le 4.5\text{ seconds}$ per turn, with the deterministic physics and parameter-sweep portion (Modules D + E) executing in $\le 150\text{ milliseconds}$ on CPU.

### 5.3 Auditability & Citation Traceability (`NFR-03`)
* Every equation solved in Module D must be accompanied by:
  1. Its canonical symbolic form in LaTeX (e.g., $C_{Di} = \frac{C_L^2}{\pi \cdot AR \cdot e}$),
  2. Its substituted SI numerical form (e.g., $C_{Di} = \frac{(0.4218)^2}{\pi \cdot 7.442 \cdot 0.80}$),
  3. Its exact source citation from the local corpus (e.g., [NASA SP-367 / NTRS 19760003955](https://ntrs.nasa.gov/search.jsp?R=19760003955), Chapter 4, or [14 CFR § 23.2110](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-23)).

### 5.4 Reliability, Fail-Fast Validation & Error Handling (`NFR-04`)
* **Physical Bounds Guardrails:** Negative or zero values for strictly positive physical quantities (`wingspan <= 0`, `wing_area <= 0`, `aircraft_mass <= 0`, `true_airspeed <= 0`), supersonic Mach numbers ($M_\infty \ge 1.0$) passed to subsonic Prandtl-Glauert formulas, or altitudes exceeding the stratosphere ceiling ($h > 20,000\text{ m}$) must immediately raise a typed `AerodynamicDomainError` caught by `orchestrator.py` and surfaced cleanly in the UI with an exact corrective message.
* **API Failover:** If the primary LLM API (`GROQ_API_KEY`) times out ($> 8.0\text{ s}$) or returns an HTTP error, `src/gatekeeper/clarifier.py` must automatically fail over to `GEMINI_API_KEY`, and if both cloud keys are unreachable, fall back to a deterministic regex + unit-parser extractor so local offline demonstrations never crash.

## 6. Appendix: Antigravity Implementation & Acceptance Test Suite

This section provides the exact repository layout, dependency manifest, JSON configurations, Pydantic schemas, core module blueprints, and automated acceptance tests required for Google Antigravity to generate the complete codebase in one pass.

### 6.1 Exact Project Repository Structure
 Note: If migrating from an existing workspace folder containing `Docs/` (with `14 CFR Part 23 (up to date as of 11-09-2026).pdf`, `19760003955.pdf`, `19840019592.pdf`, `19860017718.pdf`, and `pilot_handbook.pdf`) and `Rules/Rules.md`, copy those 5 PDFs into `data/raw_pdfs/` and retain `Rules.md` at the repository root alongside `SPEC.md`.

```text
aeroguard-rag/
├── data/
│   ├── raw_pdfs/               # NASA NTRS reports & FAA Part 23/25 PDFs
│   │   ├── 14 CFR Part 23 (up to date as of 11-09-2026).pdf
│   │   ├── 19760003955.pdf
│   │   ├── 19840019592.pdf
│   │   ├── 19860017718.pdf
│   │   └── pilot_handbook.pdf
│   ├── parsed_markdown/        # Clean Markdown + LaTeX output from MarkItDown / PyMuPDF4LLM
│   └── lightrag_storage/       # Persistent local Knowledge Graph & Vector DB
├── src/
│   ├── __init__.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── build_index.py      # Offline one-time PDF parsing & LightRAG indexing
│   ├── gatekeeper/
│   │   ├── __init__.py
│   │   ├── schemas.py          # Pydantic AircraftDesignState & required input maps
│   │   └── clarifier.py        # Missing-parameter detector & counter-questioner
│   ├── retrieval/
│   │   ├── __init__.py
│   │   └── standards_router.py # Autonomous FAA/NASA category classifier & LightRAG query
│   ├── physics_engine/
│   │   ├── __init__.py
│   │   ├── aero_solver.py      # AeroSandbox + SymPy + pint deterministic solver
│   │   └── compliance.py       # Pass/Warning/Fail rule engine + parameter-sweep advisor
│   └── orchestrator.py         # Central relay controller & state machine
├── config/
│   └── schemas_reference.json  # Hardcoded FAA/NASA limits & required input definitions
├── tests/
│   ├── __init__.py
│   ├── benchmark_prompts.json  # Automated acceptance & regression test suite data
│   └── test_acceptance.py      # Pytest runner executing all 6 acceptance tests
├── app.py                      # Split-screen Streamlit UI (Chat + Verification Dashboard)
├── requirements.txt            # Python dependencies
├── Rules.md                    # Global coding standards (YAGNI, fail fast, semantic naming)
├── SPEC.md                     # This master specification
└── .env                        # GROQ_API_KEY / GEMINI_API_KEY
```

### 6.2 Dependency Manifest (`requirements.txt`) & `.env.example`

#### `requirements.txt`
```text
# Core UI & Environment
streamlit>=1.40.0
python-dotenv>=1.0.1
pydantic>=2.9.2

# Offline Document Ingestion (Module A)
markitdown>=0.0.1a3
pymupdf4llm>=0.0.17
pymupdf>=1.24.13

# Hybrid Graph-RAG & Local CPU Embeddings (Module A & Module C)
lightrag-hku>=1.0.6
sentence-transformers>=3.2.1
torch>=2.4.0
networkx>=3.3
nano-vectordb>=0.0.4.3

# Cloud LLM Free-Tier Clients (Module B Extraction & Final Formatting Only)
groq>=0.11.0
google-genai>=0.3.0

# Deterministic Physics, Symbolic Math & Unit Engine (Module D & Module E)
aerosandbox>=4.2.4
sympy>=1.13.3
pint>=0.24.4
numpy>=1.26.4
scipy>=1.14.1

# Automated Testing
pytest>=8.3.3
```

#### `.env` Template
```ini
GROQ_API_KEY=gsk_your_free_groq_api_key_here
GEMINI_API_KEY=AIzaSy_your_free_gemini_api_key_here
DEFAULT_LLM_PROVIDER=groq
GROQ_MODEL_NAME=llama-3.3-70b-versatile
GEMINI_MODEL_NAME=gemini-2.5-flash
LIGHTRAG_STORAGE_DIR=data/lightrag_storage
RAW_PDF_DIR=data/raw_pdfs
PARSED_MARKDOWN_DIR=data/parsed_markdown
```

### 6.3 Master Regulatory & Schema Configuration (`config/schemas_reference.json`)
Antigravity must create `config/schemas_reference.json` with the following exact contents:

```json
{
  "version": "1.0.0",
  "standard_defaults": {
    "sea_level_altitude_meters": 0.0,
    "sea_level_density_kg_m3": 1.225,
    "sea_level_temperature_kelvin": 288.15,
    "sea_level_pressure_pascals": 101325.0,
    "gravitational_acceleration_m_s2": 9.80665,
    "default_oswald_efficiency_factor": 0.80,
    "default_zero_lift_drag_coefficient_cd0": 0.025,
    "default_landing_clmax": 1.60,
    "default_clean_clmax": 1.35,
    "gross_mass_per_passenger_heuristic_kg": 450.0
  },
  "intent_mandatory_parameters": {
    "induced_drag": [
      "wingspan",
      "wing_area",
      "aircraft_mass",
      "true_airspeed",
      "altitude"
    ],
    "stall_speed": [
      "wing_area",
      "aircraft_mass",
      "altitude",
      "maximum_lift_coefficient_clmax"
    ],
    "wing_loading": [
      "wing_area",
      "aircraft_mass"
    ],
    "climb_gradient": [
      "wingspan",
      "wing_area",
      "aircraft_mass",
      "true_airspeed",
      "altitude",
      "available_thrust"
    ],
    "static_margin": [
      "center_of_gravity_position",
      "neutral_point_position",
      "mean_aerodynamic_chord"
    ],
    "breguet_range": [
      "wingspan",
      "wing_area",
      "aircraft_mass",
      "fuel_mass",
      "true_airspeed",
      "altitude",
      "propeller_efficiency",
      "specific_fuel_consumption"
    ],
    "compressibility_correction": [
      "true_airspeed",
      "altitude",
      "incompressible_pressure_coefficient_cp0"
    ],
    "full_aerodynamic_audit": [
      "wingspan",
      "wing_area",
      "aircraft_mass",
      "true_airspeed",
      "altitude",
      "maximum_lift_coefficient_clmax"
    ]
  },
  "regulatory_classification_rules": {
    "FAA_14_CFR_PART_23": {
      "title": "FAA 14 CFR Part 23 — Normal/Commuter Category Airplanes",
      "max_passengers": 19,
      "max_takeoff_mass_kg": 8618.255,
      "max_takeoff_weight_lbs": 19000.0,
      "citation_section": "14 CFR § 23.2005 & § 23.2110 (Historic § 23.49)",
      "source_file": "14 CFR Part 23 (up to date as of 11-09-2026).pdf"
    },
    "FAA_14_CFR_PART_25": {
      "title": "FAA 14 CFR Part 25 — Transport Category Airplanes",
      "min_passengers_exclusive": 19,
      "min_takeoff_mass_kg_exclusive": 8618.255,
      "citation_section": "14 CFR § 25.1 & § 25.103 / § 25.121",
      "source_file": "14_CFR_Part_25.pdf"
    }
  },
  "compliance_thresholds": {
    "FAA_14_CFR_PART_23": {
      "stall_speed_vs0_knots": {
        "pass_max": 58.0,
        "warning_max": 61.0,
        "fail_above": 61.0,
        "unit": "knots",
        "regulation_reference": "14 CFR § 23.2110 / § 23.49 (Max Landing Stall Speed Vs0 <= 61 knots)",
        "source_document": "14 CFR Part 23 (up to date as of 11-09-2026).pdf"
      },
      "induced_drag_coefficient_cdi": {
        "pass_max": 0.040,
        "warning_max": 0.065,
        "fail_above": 0.065,
        "unit": "dimensionless",
        "regulation_reference": "NASA SP-367 (NTRS 19760003955) Ch. 4 Subsonic Induced Drag Efficiency",
        "source_document": "19760003955.pdf"
      },
      "aspect_ratio_ar": {
        "pass_min": 6.5,
        "warning_min": 5.0,
        "fail_below": 5.0,
        "unit": "dimensionless",
        "regulation_reference": "NASA SP-367 (NTRS 19760003955) & FAA-H-8083-25C Ch. 5 Planform Design",
        "source_document": "19760003955.pdf"
      },
      "static_margin_fraction": {
        "pass_min": 0.05,
        "pass_max": 0.25,
        "warning_min": 0.02,
        "warning_max": 0.35,
        "unit": "fraction_mac",
        "regulation_reference": "14 CFR § 23.2135 Static Longitudinal Stability & NASA SP-367 Ch. 7",
        "source_document": "14 CFR Part 23 (up to date as of 11-09-2026).pdf"
      },
      "climb_gradient_percent": {
        "pass_min": 8.33,
        "warning_min": 6.0,
        "fail_below": 6.0,
        "unit": "percent",
        "regulation_reference": "14 CFR § 23.2120 Climb Requirements (1:12 gradient = 8.33%)",
        "source_document": "14 CFR Part 23 (up to date as of 11-09-2026).pdf"
      }
    },
    "FAA_14_CFR_PART_25": {
      "stall_speed_vs0_knots": {
        "pass_max": 135.0,
        "warning_max": 145.0,
        "fail_above": 145.0,
        "unit": "knots",
        "regulation_reference": "14 CFR § 25.103 Stall Speed & Approach Category C/D Envelope",
        "source_document": "pilot_handbook.pdf"
      },
      "induced_drag_coefficient_cdi": {
        "pass_max": 0.035,
        "warning_max": 0.055,
        "fail_above": 0.055,
        "unit": "dimensionless",
        "regulation_reference": "NASA CP-2208 (NTRS 19840019592) Energy Efficient Transport Wing",
        "source_document": "19840019592.pdf"
      },
      "aspect_ratio_ar": {
        "pass_min": 7.0,
        "warning_min": 5.5,
        "fail_below": 5.5,
        "unit": "dimensionless",
        "regulation_reference": "NASA CP-2208 (NTRS 19840019592) Supercritical High-AR Wing Research",
        "source_document": "19840019592.pdf"
      }
    }
  },
  "parameter_sweep_config": {
    "wingspan_sweep_max_ratio": 1.30,
    "wingspan_sweep_extended_max_ratio": 1.60,
    "wingspan_step_meters": 0.20,
    "wing_area_step_m2": 0.50,
    "clmax_sweep_max": 2.20,
    "clmax_step": 0.05
  }
}
```

### 6.4 Pydantic State & Data Schemas (`src/gatekeeper/schemas.py`)
Antigravity must implement `src/gatekeeper/schemas.py` with verbose, self-documenting attribute names conforming to `Rules.md`:

```python
from __future__ import annotations
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

CalculationIntentType = Literal[
    "induced_drag",
    "stall_speed",
    "wing_loading",
    "climb_gradient",
    "static_margin",
    "breguet_range",
    "compressibility_correction",
    "full_aerodynamic_audit",
    "out_of_scope",
]

PipelineStatusType = Literal[
    "INITIALIZED",
    "HALTED_MISSING_PARAMS",
    "READY_FOR_PHYSICS",
    "COMPLETED_VERIFIED",
    "OUT_OF_SCOPE_HALT",
    "DOMAIN_ERROR",
]

ComplianceStatusType = Literal["PASS", "WARNING", "FAIL", "AWAITING_PARAMETERS"]


class DimensionalQuantityInput(BaseModel):
    """Represents a user-supplied physical quantity with its raw unit string prior to Pint SI conversion."""
    numerical_value: float = Field(..., description="Raw numeric scalar extracted from user prompt")
    unit_string: str = Field(..., description="Raw unit string such as 'm', 'ft', 'knots', 'm/s', 'kg', 'lbs'")


class UnitConversionRecord(BaseModel):
    """Auditable record of Pint unit normalization from user units to SI base units."""
    parameter_name: str
    input_value: float
    input_unit: str
    si_value: float
    si_unit: str


class EquationTrace(BaseModel):
    """Symbolic and substituted mathematical trace for a single aerodynamic equation."""
    equation_name: str
    symbolic_latex: str
    substituted_latex: str
    output_variable_name: str
    output_value_si: float
    output_unit_si: str
    secondary_display_value: Optional[float] = None
    secondary_display_unit: Optional[str] = None
    source_citation_id: str


class RegulatoryCitation(BaseModel):
    """Verbatim citation retrieved from the local NASA NTRS / FAA CFR LightRAG index."""
    citation_id: str
    document_title: str
    source_pdf_filename: str
    section_or_report_number: str
    verbatim_excerpt: str
    relevance_score: float = 1.0


class SweepStepRecord(BaseModel):
    """Single step in an AeroSandbox deterministic geometry parameter sweep."""
    step_index: int
    swept_parameter_name: str
    swept_parameter_value_si: float
    computed_aspect_ratio: float
    computed_cdi: float
    computed_induced_drag_newtons: float
    computed_stall_speed_knots: float
    achieves_compliance: bool


class DesignAdvisory(BaseModel):
    """Conditional geometry modification recommendation generated ONLY when status is WARNING or FAIL."""
    triggered_by_rule: str
    swept_parameter_name: str
    original_value_si: float
    recommended_value_si: float
    unit_si: str
    absolute_delta_si: float
    percentage_change: float
    projected_metric_name: str
    projected_metric_value: float
    projected_metric_unit: str
    within_thirty_percent_sweep_window: bool
    recommendation_summary: str
    sweep_trajectory: List[SweepStepRecord] = Field(default_factory=list)


class RuleCheckResult(BaseModel):
    """Evaluation result of a single regulatory or aerodynamic threshold rule."""
    rule_id: str
    metric_name: str
    computed_value: float
    metric_unit: str
    threshold_description: str
    status: Literal["PASS", "WARNING", "FAIL"]
    regulation_reference: str
    source_document: str


class ComplianceReport(BaseModel):
    """Complete Module E output grading deterministic outputs and holding optional design advisory."""
    overall_status: ComplianceStatusType
    regulatory_category: str
    certification_level_description: str
    rule_checks: List[RuleCheckResult] = Field(default_factory=list)
    design_advisory: Optional[DesignAdvisory] = None


class PhysicsSolutionBundle(BaseModel):
    """Complete deterministic output bundle produced by Module D (AeroSandbox + SymPy + Pint)."""
    altitude_meters: float
    air_density_kg_m3: float
    static_pressure_pascals: float
    temperature_kelvin: float
    speed_of_sound_m_s: float
    dynamic_pressure_pascals: Optional[float] = None
    aspect_ratio: Optional[float] = None
    wing_loading_n_m2: Optional[float] = None
    wing_loading_kg_m2: Optional[float] = None
    lift_coefficient_cl: Optional[float] = None
    induced_drag_coefficient_cdi: Optional[float] = None
    induced_drag_force_newtons: Optional[float] = None
    total_drag_coefficient_cd: Optional[float] = None
    total_drag_force_newtons: Optional[float] = None
    lift_to_drag_ratio: Optional[float] = None
    stall_speed_vs0_m_s: Optional[float] = None
    stall_speed_vs0_knots: Optional[float] = None
    mach_number: Optional[float] = None
    reynolds_number: Optional[float] = None
    prandtl_glauert_cp_corrected: Optional[float] = None
    static_margin_fraction: Optional[float] = None
    climb_gradient_percent: Optional[float] = None
    breguet_range_kilometers: Optional[float] = None
    equation_traces: List[EquationTrace] = Field(default_factory=list)


class AircraftDesignState(BaseModel):
    """Persistent multi-turn session state managed by orchestrator.py across the 5-module relay."""
    session_id: str = "default-aeroguard-session"
    turn_index: int = 0
    calculation_intent: Optional[CalculationIntentType] = None
    pipeline_status: PipelineStatusType = "INITIALIZED"

    # Primary Boundary Conditions (stored with user units prior to Module D Pint SI normalization)
    wingspan: Optional[DimensionalQuantityInput] = None
    wing_area: Optional[DimensionalQuantityInput] = None
    aircraft_mass: Optional[DimensionalQuantityInput] = None
    passenger_count: Optional[int] = None
    true_airspeed: Optional[DimensionalQuantityInput] = None
    altitude: Optional[DimensionalQuantityInput] = None

    # Secondary / Aerodynamic Coefficients & Stability Inputs
    oswald_efficiency_factor: float = 0.80
    zero_lift_drag_coefficient_cd0: float = 0.025
    maximum_lift_coefficient_clmax: Optional[float] = None
    available_thrust: Optional[DimensionalQuantityInput] = None
    center_of_gravity_position: Optional[DimensionalQuantityInput] = None
    neutral_point_position: Optional[DimensionalQuantityInput] = None
    mean_aerodynamic_chord: Optional[DimensionalQuantityInput] = None
    fuel_mass: Optional[DimensionalQuantityInput] = None
    propeller_efficiency: Optional[float] = None
    specific_fuel_consumption: Optional[DimensionalQuantityInput] = None
    incompressible_pressure_coefficient_cp0: Optional[float] = None

    # Relay Artifacts
    missing_parameters: List[str] = Field(default_factory=list)
    regulatory_category: Optional[str] = None
    certification_level: Optional[str] = None
    unit_conversions: List[UnitConversionRecord] = Field(default_factory=list)
    retrieved_citations: List[RegulatoryCitation] = Field(default_factory=list)
    latest_physics_solution: Optional[PhysicsSolutionBundle] = None
    latest_compliance_report: Optional[ComplianceReport] = None
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
```

### 6.5 Core Module Implementation Blueprints for Antigravity

#### 6.5.1 Module D Physics & Unit Normalization Blueprint (`src/physics_engine/aero_solver.py`)
Antigravity must implement `src/physics_engine/aero_solver.py` following this deterministic mathematical pattern:
1. **Pint SI Conversion Helper:**
   ```python
   import math
   import pint
   import sympy as sp
   import aerosandbox as asb
   from src.gatekeeper.schemas import (
       AircraftDesignState,
       DimensionalQuantityInput,
       EquationTrace,
       PhysicsSolutionBundle,
       UnitConversionRecord,
   )

   UNIT_REGISTRY = pint.UnitRegistry()
   STANDARD_GRAVITY_M_S2 = 9.80665

   def convert_quantity_to_si(
       parameter_name: str,
       quantity_input: DimensionalQuantityInput,
       target_si_unit: str,
   ) -> tuple[float, UnitConversionRecord]:
       normalized_unit = quantity_input.unit_string.strip().lower()
       unit_aliases = {
           "kts": "knot",
           "knots": "knot",
           "kt": "knot",
           "sqm": "meter ** 2",
           "m^2": "meter ** 2",
           "m2": "meter ** 2",
           "sq ft": "foot ** 2",
           "ft^2": "foot ** 2",
           "ft2": "foot ** 2",
           "lbs": "pound",
           "lb": "pound",
           "lbf": "pound_force",
       }
       resolved_unit = unit_aliases.get(normalized_unit, normalized_unit)
       pint_quantity = UNIT_REGISTRY.Quantity(quantity_input.numerical_value, resolved_unit)

       # Handle weight-to-mass conversion if user supplied force units (N or lbf) for aircraft_mass
       if target_si_unit == "kilogram" and pint_quantity.check("[force]"):
           force_newtons = float(pint_quantity.to("newton").magnitude)
           mass_kilograms = force_newtons / STANDARD_GRAVITY_M_S2
           return mass_kilograms, UnitConversionRecord(
               parameter_name=parameter_name,
               input_value=quantity_input.numerical_value,
               input_unit=quantity_input.unit_string,
               si_value=round(mass_kilograms, 6),
               si_unit="kg",
           )

       converted_quantity = pint_quantity.to(target_si_unit)
       si_float = float(converted_quantity.magnitude)
       return si_float, UnitConversionRecord(
           parameter_name=parameter_name,
           input_value=quantity_input.numerical_value,
           input_unit=quantity_input.unit_string,
           si_value=round(si_float, 6),
           si_unit=target_si_unit,
       )
   ```
2. **AeroSandbox + SymPy Solver Execution:**
   * Compute `atmosphere = asb.Atmosphere(altitude=altitude_meters)` to obtain `air_density_kg_m3 = float(atmosphere.density())`, `static_pressure_pascals = float(atmosphere.pressure())`, `temperature_kelvin = float(atmosphere.temperature())`, and `speed_of_sound_m_s = float(atmosphere.speed_of_sound())`.
   * Construct `SymPy` symbols (`W_sym, rho_sym, V_sym, S_sym, b_sym, e_sym, CL_sym, AR_sym, CLmax_sym`) and evaluate both the symbolic LaTeX representation (`sp.latex(...)`) and exact numerical values.

#### 6.5.2 Module E Conditional Parameter-Sweep Blueprint (`src/physics_engine/compliance.py`)
* When `overall_status == "PASS"`: set `design_advisory = None`.
* When `overall_status in ("WARNING", "FAIL")`:
  * If `stall_speed_vs0_knots > 58.0`: sweep candidate wingspan $b_{\text{cand}} = b_0 + k \cdot 0.20\text{ m}$ (keeping mean geometric chord $\bar{c}_0 = S_0 / b_0$ constant so planform area scales proportionally $S_{\text{cand}} = b_{\text{cand}} \cdot \bar{c}_0$, or sweeping $S_{\text{cand}}$ directly if wingspan is not set) up to $+30\%$ ($1.30 \cdot b_0$) and extended up to $1.60 \cdot b_0$ if needed, computing $V_{s0}(b_{\text{cand}}) = \sqrt{\frac{2 W}{\rho \cdot (b_{\text{cand}} \cdot \bar{c}_0) \cdot C_{L,\max}}}$ at each step until $V_{s0} \le 61.0\text{ knots}$ (for `FAIL` recovery) or $\le 58.0\text{ knots}$ (for `PASS` recovery).
  * If `induced_drag_coefficient_cdi > 0.040`: sweep candidate wingspan $b_{\text{cand}}$ from $b_0$ up to $1.30 \cdot b_0$ in $+0.20\text{ m}$ increments at constant $S_0$ (where $AR_{\text{cand}} = b_{\text{cand}}^2 / S_0$ and $C_{Di,\text{cand}} = \frac{C_L^2}{\pi \cdot AR_{\text{cand}} \cdot e}$) to find the minimum wingspan that reduces $C_{Di} \le 0.040$.

### 6.6 End-to-End Acceptance Test Suite (`tests/benchmark_prompts.json`)
Antigravity must populate `tests/benchmark_prompts.json` and verify that all 6 end-to-end test cases pass via `pytest tests/test_acceptance.py`:

| Test ID | Scenario Name | Input User Turn(s) | Expected Pipeline Status & Regulatory Route | Expected Deterministic Math & Advisory Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | **Incomplete Query Triggering Active Counter-Questioning** | **Turn 1:** `"Calculate the induced drag for my 4-seat prototype aircraft with a 10.5 m wingspan."` | `pipeline_status = "HALTED_MISSING_PARAMS"`; `missing_parameters = ["wing_area", "aircraft_mass", "true_airspeed", "altitude"]`; `regulatory_category = "FAA_14_CFR_PART_23"` | Module D (`aero_solver.py`) is **NOT** called. Module B (`clarifier.py`) outputs a counter-question requesting `wing_area`, `aircraft_mass`, `true_airspeed`, and `altitude` (or ISA sea-level confirmation). |
| **TC-02** | **Multi-Turn State Retention & Resume Execution** | **Turn 1:** (Same as TC-01)<br>**Turn 2:** `"Wing area is 15.0 m^2, gross mass is 1100 kg, cruise airspeed is 60 m/s, and assume standard ISA sea-level conditions."` | `pipeline_status = "COMPLETED_VERIFIED"`; retains `wingspan = 10.5 m` and `passenger_count = 4` from Turn 1; merges `wing_area = 15.0 m²`, `aircraft_mass = 1100 kg`, `true_airspeed = 60.0 m/s`, `altitude = 0.0 m`. | $\rho = 1.225\text{ kg/m}^3$, $q_\infty = 2205.0\text{ Pa}$, $W = 10787.315\text{ N}$, $AR = \frac{10.5^2}{15.0} = 7.350$, $C_L = \frac{10787.315}{2205.0 \times 15.0} = 0.32615$, $C_{Di} = \frac{0.32615^2}{\pi \times 7.350 \times 0.80} = 0.005759$, $D_i = 190.47\text{ N}$. Status: `PASS`. |
| **TC-03** | **FAA Part 23 Compliance `PASS` with Strictly Silent Advisor** | **Turn 1:** `"Run a full aerodynamic and stall speed audit for a 4-passenger aircraft at sea level (0 m): wingspan 11.0 m, wing area 16.2 m^2, gross mass 1050 kg, cruise speed 62 m/s, and landing CLmax of 1.65."` | `pipeline_status = "COMPLETED_VERIFIED"`; `regulatory_category = "FAA_14_CFR_PART_23"`; `overall_status = "PASS"` | $W = 10296.98\text{ N}$, $AR = 7.4691$, $V_{s0} = \sqrt{\frac{2 \times 10296.98}{1.225 \times 16.2 \times 1.65}} = 25.087\text{ m/s} = 48.765\text{ knots} \le 58.0\text{ knots}$ (`PASS`). $C_{Di} = 0.00441 \le 0.040$ (`PASS`). **`design_advisory` MUST be `None` (Silent Advisor).** |
| **TC-04** | **FAA Part 23 Compliance `FAIL` Triggering Deterministic Wingspan Sweep** | **Turn 1:** `"Evaluate stall speed and induced drag compliance for a 6-passenger commuter aircraft at sea level (0 m) with wingspan 8.4 m, wing area 10.5 m^2, gross mass 1850 kg, cruise speed 52 m/s, and landing CLmax 1.35."` | `pipeline_status = "COMPLETED_VERIFIED"`; `regulatory_category = "FAA_14_CFR_PART_23"`; `overall_status = "FAIL"` | $W = 18142.30\text{ N}$, $AR = 6.720$, $V_{s0} = \sqrt{\frac{2 \times 18142.30}{1.225 \times 10.5 \times 1.35}} = 45.702\text{ m/s} = 88.838\text{ knots} > 61.0\text{ knots}$ (`FAIL` per [14 CFR § 23.2110](https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-23)). $C_L = 1.0450$, $C_{Di} = 0.06466$ (`WARNING`). **Conditional Advisor triggers:** runs AeroSandbox parameter sweep and outputs exact required geometry/high-lift modification. |
| **TC-05** | **Mixed Imperial & Aviation Unit Conversion via Pint** | **Turn 1:** `"Compute induced drag and wing loading for a 25-passenger regional transport aircraft with wingspan 95 ft, wing area 850 sq ft, gross weight 42000 lbs, flying at 220 knots at an altitude of 10000 ft."` | `pipeline_status = "COMPLETED_VERIFIED"`; `regulatory_category = "FAA_14_CFR_PART_25"` (auto-routed via `25 pax > 19` and `19050.88 kg > 8618.26 kg`). | Pint converts: $b = 95\text{ ft} \rightarrow 28.956\text{ m}$, $S = 850\text{ ft}^2 \rightarrow 78.9676\text{ m}^2$, $m = 42000\text{ lbs} \rightarrow 19050.88\text{ kg}$ ($W = 186825.3\text{ N}$), $V_\infty = 220\text{ knots} \rightarrow 113.178\text{ m/s}$, $h = 10000\text{ ft} \rightarrow 3048.0\text{ m}$ ($\rho = 0.90464\text{ kg/m}^3$). $AR = 10.618$, $W/S = 2365.85\text{ N/m}^2$, $C_L = 0.4085$, $C_{Di} = 0.00625$, $D_i = 2857.4\text{ N}$. |
| **TC-06** | **Out-of-Scope / Missing Document Graceful Handling** | **Turn 1:** `"Calculate the orbitalohmann transfer delta-V for a geostationary communication satellite and check NASA structural titanium creep limits at 1400 Kelvin."` | `pipeline_status = "OUT_OF_SCOPE_HALT"`; `calculation_intent = "out_of_scope"` | System halts gracefully without invoking `aero_solver.py` or hallucinating orbital mechanics/metallurgy rules, explicitly stating that the query falls outside the fixed-wing atmospheric aerodynamics and FAA Part 23/25 airworthiness corpus. |

#### `tests/benchmark_prompts.json` (Machine-Readable Test File)
```json
{
  "test_suite_name": "AeroGuard-RAG IEEE 830 Acceptance Suite",
  "tests": [
    {
      "test_id": "TC-01",
      "description": "Incomplete query triggering active counter-questioning gatekeeper halt",
      "turns": [
        "Calculate the induced drag for my 4-seat prototype aircraft with a 10.5 m wingspan."
      ],
      "expected": {
        "pipeline_status": "HALTED_MISSING_PARAMS",
        "calculation_intent": "induced_drag",
        "missing_parameters": ["wing_area", "aircraft_mass", "true_airspeed", "altitude"],
        "solver_invoked": false
      }
    },
    {
      "test_id": "TC-02",
      "description": "Multi-turn state retention merging Turn 1 and Turn 2 parameters",
      "turns": [
        "Calculate the induced drag for my 4-seat prototype aircraft with a 10.5 m wingspan.",
        "Wing area is 15.0 m^2, gross mass is 1100 kg, cruise airspeed is 60 m/s, and assume standard ISA sea-level conditions."
      ],
      "expected": {
        "pipeline_status": "COMPLETED_VERIFIED",
        "regulatory_category": "FAA_14_CFR_PART_23",
        "aspect_ratio": 7.35,
        "lift_coefficient_cl": 0.32615,
        "induced_drag_coefficient_cdi": 0.00576,
        "induced_drag_force_newtons": 190.47,
        "compliance_status": "PASS",
        "design_advisory_present": false
      }
    },
    {
      "test_id": "TC-03",
      "description": "FAA Part 23 compliance PASS with silent design advisor",
      "turns": [
        "Run a full aerodynamic and stall speed audit for a 4-passenger aircraft at sea level (0 m): wingspan 11.0 m, wing area 16.2 m^2, gross mass 1050 kg, cruise speed 62 m/s, and landing CLmax of 1.65."
      ],
      "expected": {
        "pipeline_status": "COMPLETED_VERIFIED",
        "regulatory_category": "FAA_14_CFR_PART_23",
        "stall_speed_vs0_knots": 48.765,
        "compliance_status": "PASS",
        "design_advisory_present": false
      }
    },
    {
      "test_id": "TC-04",
      "description": "FAA Part 23 stall speed FAIL (> 61 knots) triggering deterministic AeroSandbox parameter sweep",
      "turns": [
        "Evaluate stall speed and induced drag compliance for a 6-passenger commuter aircraft at sea level (0 m) with wingspan 8.4 m, wing area 10.5 m^2, gross mass 1850 kg, cruise speed 52 m/s, and landing CLmax 1.35."
      ],
      "expected": {
        "pipeline_status": "COMPLETED_VERIFIED",
        "regulatory_category": "FAA_14_CFR_PART_23",
        "stall_speed_vs0_knots": 88.838,
        "compliance_status": "FAIL",
        "design_advisory_present": true,
        "swept_parameter_name": "wingspan"
      }
    },
    {
      "test_id": "TC-05",
      "description": "Mixed Imperial/Aviation units converted via Pint and routed to FAA Part 25",
      "turns": [
        "Compute induced drag and wing loading for a 25-passenger regional transport aircraft with wingspan 95 ft, wing area 850 sq ft, gross weight 42000 lbs, flying at 220 knots at an altitude of 10000 ft."
      ],
      "expected": {
        "pipeline_status": "COMPLETED_VERIFIED",
        "regulatory_category": "FAA_14_CFR_PART_25",
        "si_wingspan_meters": 28.956,
        "si_wing_area_m2": 78.9676,
        "si_mass_kg": 19050.88,
        "si_airspeed_m_s": 113.178,
        "si_altitude_meters": 3048.0,
        "aspect_ratio": 10.618,
        "induced_drag_force_newtons": 2857.4,
        "compliance_status": "PASS"
      }
    },
    {
      "test_id": "TC-06",
      "description": "Out-of-scope orbital/materials query handled gracefully without hallucination",
      "turns": [
        "Calculate the orbital Hohmann transfer delta-V for a geostationary communication satellite and check NASA structural titanium creep limits at 1400 Kelvin."
      ],
      "expected": {
        "pipeline_status": "OUT_OF_SCOPE_HALT",
        "calculation_intent": "out_of_scope",
        "solver_invoked": false
      }
    }
  ]
}
```

### 6.7 Antigravity Execution Order Checklist
When handing this `SPEC.md` to Google Antigravity, the agentic IDE shall execute the build in the following strict deterministic order:
1. Scaffold the directory structure (`data/raw_pdfs/`, `data/parsed_markdown/`, `data/lightrag_storage/`, `src/ingestion/`, `src/gatekeeper/`, `src/retrieval/`, `src/physics_engine/`, `config/`, `tests/`) and copy existing PDFs from `Docs/` into `data/raw_pdfs/`.
2. Write `requirements.txt`, `config/schemas_reference.json`, and `tests/benchmark_prompts.json`.
3. Implement `src/gatekeeper/schemas.py` and `src/gatekeeper/clarifier.py` (including cloud LLM JSON extraction + deterministic regex fallback).
4. Implement `src/ingestion/build_index.py` and `src/retrieval/standards_router.py`.
5. Implement `src/physics_engine/aero_solver.py` and `src/physics_engine/compliance.py`.
6. Implement `src/orchestrator.py` and `app.py`.
7. Implement `tests/test_acceptance.py` and run `pytest tests/test_acceptance.py -v` until 6/6 acceptance tests pass with zero warnings or errors.
