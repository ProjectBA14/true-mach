"""Active Counter-Questioning Gatekeeper: Intent extraction, missing boundary-condition inspection, and clarification."""

from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from src.gatekeeper.schemas import (
    AircraftDesignState,
    CalculationIntentType,
    DimensionalQuantityInput,
    ExtractedTurnParameters,
)

load_dotenv()

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "schemas_reference.json"


def load_schema_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def normalize_text_commas(text: str) -> str:
    """Normalize formatted numbers with thousands-separator commas (e.g., '18,500' -> '18500')."""
    return re.sub(r'(?<=\d),(?=\d{3}\b)', '', text)


def extract_parameters_local_deterministic(user_text: str) -> ExtractedTurnParameters:
    """Deterministic regex & keyword extractor that consumes zero API tokens."""
    user_text = normalize_text_commas(user_text)
    text_lower = user_text.lower()

    # 1. Out-of-scope intent detection (non-Earth atmospheres, spaceflight, orbital mechanics)
    out_of_scope_keywords = [
        "orbital", "hohmann", "satellite", "titanium creep", "delta-v",
        "interplanetary", "kelvin", "spacecraft", "geostationary",
        "mars", "martian", "venus", "venusian", "titan", "jupiter", "moon", "lunar",
        "extraterrestrial", "non-earth", "alien atmosphere",
    ]
    if any(kw in text_lower for kw in out_of_scope_keywords):
        return ExtractedTurnParameters(calculation_intent="out_of_scope")

    # 2. Intent classification
    intent: Optional[CalculationIntentType] = None

    # Regulatory and conceptual patterns (singular and plural)
    regulatory_patterns = [
        r"\bstandards?\b",
        r"\bregulations?\b",
        r"\brequirements?\b",
        r"\brules?\b",
        r"\bcertifications?\b",
        r"\bairworthiness\b",
        r"\bpart\s*23\b",
        r"\bpart\s*25\b",
        r"\bfar\b",
        r"\bcfr\b",
        r"\bac\s*23(?:-[0-9a-zA-Z]+)?\b",
        r"\bac\s*25(?:-[0-9a-zA-Z]+)?\b",
    ]

    explanatory_patterns = [
        r"\bexplain\b",
        r"\bwhat\s+(?:is|are)\b",
        r"\blist\b",
        r"\bdescribe\b",
        r"\btell\s+me\s+about\b",
        r"\bhow\s+does\b",
        r"\bdifference\s+between\b",
        r"\bguide\b",
        r"\boverview\b",
    ]

    aircraft_category_patterns = [
        r"\bnormal\b",
        r"\bcommuter\b",
        r"\btransport\b",
        r"\bpassenger\s+aircraft\b",
        r"\bpassenger\s+plane\b",
        r"\bnormal\s+plane\b",
        r"\bcommercial\b",
        r"\bgeneral\s+aviation\b",
    ]

    has_numerical_input = bool(
        re.search(r"\d+(?:\.\d+)?\s*(?:m\b|meter|meters|ft\b|feet|kg\b|kgs|lbs?\b|pound|pounds|knots?\b|kts?\b|m/s\b|mps\b|sq\s*ft|sqft|m\^?2|deg|degrees|%|mach)", text_lower)
        or re.search(r"\b(?:wingspan|wing\s*area|gross\s*mass|gross\s*weight|mass|weight|speed|airspeed|altitude)\s*(?:of|is|:)?\s*\d+", text_lower)
    )

    has_design_calculation_request = bool(
        re.search(r"\b(calculate|compute|solve|sizing|evaluate|sweep)\b", text_lower)
        and not re.search(r"\b(how to calculate|how do you compute|how is.*calculated)\b", text_lower)
    )

    # Sizing / Target parameter queries (e.g., "what should the wingspan be?", "what would be the most applicable wingspan?", "size the wing")
    is_wing_sizing_query = bool(
        re.search(
            r"(?:what|how\s+much|which)\s+(?:should|would\s+be|is)\s+(?:the\s+)?(?:most\s+applicable\s+|optimal\s+|recommended\s+|required\s+|suitable\s+|appropriate\s+)?(?:wing\s*span|wingspan)",
            text_lower,
        )
        or re.search(r"\b(?:size\s+(?:the\s+)?wing|wing\s+sizing|size\s+wingspan|wingspan\s+sizing)\b", text_lower)
        or re.search(r"\b(?:recommend|determine|find|calculate|suggest)\s+(?:a|the)?\s*(?:applicable|optimal|compliant|required|suitable)?\s*(?:wing\s*span|wingspan)\b", text_lower)
        or re.search(r"(?:most\s+applicable|optimal|recommended|required|suitable)\s+(?:wing\s*span|wingspan)", text_lower)
    )

    if is_wing_sizing_query:
        intent = "wing_sizing"

    # Strip atmospheric default phrases so "standard ISA" / "standard atmospheric conditions" does not trigger regulatory QA
    clean_reg_text = re.sub(
        r"\bstandard\s+atmospher\w*(?:\s+conditions?)?\b|\bstandard\s+isa(?:\s+conditions?)?\b|\bisa\s+standard\b|\bisa\s+defaults?\b|\bstandard\s+conditions?\b",
        "",
        text_lower,
    )

    has_regulatory_term = any(re.search(p, clean_reg_text) for p in regulatory_patterns)
    has_explanatory_verb = any(re.search(p, text_lower) for p in explanatory_patterns)
    has_category_term = any(re.search(p, text_lower) for p in aircraft_category_patterns)

    # Zero-numeric conceptual guard:
    # If no numerical inputs/units AND (matches regulatory terms OR matches explanatory verb + category OR mentions aircraft categories without design calculation)
    if intent is None and not has_numerical_input and not has_design_calculation_request:
        if (
            has_regulatory_term
            or (has_explanatory_verb and has_category_term)
            or (has_category_term and any(w in text_lower for w in ["plane", "aircraft", "airplane"]))
        ):
            intent = "regulatory_qa"

    if intent is None:
        if has_regulatory_term and not has_numerical_input:
            intent = "regulatory_qa"
        elif any(kw in text_lower for kw in ["transonic", "wave drag", "drag divergence", "korn", "critical mach", "supercritical"]):
            intent = "transonic_audit"
        elif "full aerodynamic" in text_lower or ("audit" in text_lower and "stall" in text_lower):
            intent = "full_aerodynamic_audit"
        elif "induced drag" in text_lower and "stall speed" in text_lower:
            intent = "stall_speed"
        elif "induced drag" in text_lower:
            intent = "induced_drag"
        elif "stall speed" in text_lower:
            intent = "stall_speed"
        elif "wing loading" in text_lower:
            intent = "wing_loading"
        elif "climb gradient" in text_lower:
            intent = "climb_gradient"
        elif "static margin" in text_lower:
            intent = "static_margin"
        elif "breguet" in text_lower or "range" in text_lower:
            intent = "breguet_range"
        elif "compressibility" in text_lower:
            intent = "compressibility_correction"
        elif has_regulatory_term and not has_numerical_input:
            intent = "regulatory_qa"

    # 3. Passenger count
    pax: Optional[int] = None
    pax_match = re.search(r"(\d+)\s*(?:-| )?(?:passenger|seat|pax)", text_lower)
    if pax_match:
        pax = int(pax_match.group(1))

    # 4. Wingspan
    span: Optional[DimensionalQuantityInput] = None
    if not is_wing_sizing_query:
        span_match = re.search(r"(\d+(?:\.\d+)?)\s*(m|meter|meters|ft|feet)\s*wingspan", text_lower)
        if not span_match:
            span_match = re.search(r"wingspan(?:\s*(?:of|is|:))?\s*(\d+(?:\.\d+)?)\s*(m|meters|meter|ft|feet)", text_lower)
        if not span_match:
            span_match = re.search(r"(?:span|b)(?:\s*(?:of|is|:))?\s*(\d+(?:\.\d+)?)\s*(m|meters|meter|ft|feet)\b", text_lower)
        if span_match:
            val = float(span_match.group(1))
            if val > 0:
                span = DimensionalQuantityInput(
                    numerical_value=val,
                    unit_string=span_match.group(2).strip(),
                )

    # 5. Wing Area
    area: Optional[DimensionalQuantityInput] = None
    area_match = re.search(r"(\d+(?:\.\d+)?)\s*(m\^2|m2|sqm|sq\s*ft|sqft|ft\^2|ft2)\s*wing\s*area", text_lower)
    if not area_match:
        area_match = re.search(r"wing\s*area(?:\s*(?:of|is|:))?\s*(\d+(?:\.\d+)?)\s*(m\^2|m2|sqm|sq\s*ft|sqft|ft\^2|ft2)", text_lower)
    if not area_match:
        area_match = re.search(r"(?:planform\s*area|wing\s*surface|s)(?:\s*(?:of|is|:))?\s*(\d+(?:\.\d+)?)\s*(m\^2|m2|sqm|sq\s*ft|sqft|ft\^2|ft2)", text_lower)
    if not area_match:
        area_match = re.search(r"(\d+(?:\.\d+)?)\s*(m\^2|m2|sqm|sq\s*ft|sqft|ft\^2|ft2)\s*(?:wing|planform)", text_lower)
    if area_match:
        val = float(area_match.group(1))
        if val > 0:
            area = DimensionalQuantityInput(
                numerical_value=val,
                unit_string=area_match.group(2).strip(),
            )

    # 6. Aircraft Mass / Gross Weight
    mass: Optional[DimensionalQuantityInput] = None
    mass_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(kg|kgs|lbs|lb|lbf|newtons|n)\s*(?:gross\s*mass|gross\s*weight|weight|mass|mtow)",
        text_lower,
    )
    if not mass_match:
        mass_match = re.search(
            r"(?:gross\s*mass|gross\s*weight|mass|weight|mtow)(?:\s*(?:of|is|:))?\s*(\d+(?:\.\d+)?)\s*(kg|kgs|lbs|lb|lbf|newtons|n)",
            text_lower,
        )
    if not mass_match:
        mass_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(kg|kgs|lbs|lb|lbf|newtons|n)\s*(?:aircraft|plane|airplane|commuter|transport)",
            text_lower,
        )
    if not mass_match:
        for candidate in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(kg|kgs|lbs|lb|lbf)\b", text_lower):
            start_pos = candidate.start()
            prefix = text_lower[max(0, start_pos - 15):start_pos]
            if "fuel" not in prefix and "payload" not in prefix:
                mass_match = candidate
                break
    if mass_match:
        val = float(mass_match.group(1))
        if val > 0:
            mass = DimensionalQuantityInput(
                numerical_value=val,
                unit_string=mass_match.group(2).strip(),
            )

    # 7. True Airspeed / Cruise Speed / Mach Number
    speed: Optional[DimensionalQuantityInput] = None
    speed_match = re.search(
        r"(?:cruise\s*airspeed|cruise\s*speed|airspeed|true\s*airspeed|speed|flying\s*at)(?:\s*(?:of|is|:))?\s*(\d+(?:\.\d+)?)\s*(knots|kts|kt|m/s|mps)",
        text_lower,
    )
    if not speed_match:
        speed_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(knots|kts|kt|m/s|mps)\s*(?:cruise\s*airspeed|cruise\s*speed|airspeed|speed)",
            text_lower,
        )
    if not speed_match:
        # Match Mach number e.g. "mach 0.78", "m = 0.82", "0.80 mach"
        mach_match = re.search(r"(?:mach|m\s*=)\s*(0\.\d+|\d+(?:\.\d+)?)", text_lower)
        if not mach_match:
            mach_match = re.search(r"(0\.\d+)\s*mach", text_lower)
        if mach_match:
            val = float(mach_match.group(1))
            if val > 0:
                speed = DimensionalQuantityInput(
                    numerical_value=val,
                    unit_string="mach",
                )
    if speed_match and speed is None:
        val = float(speed_match.group(1))
        if val > 0:
            speed = DimensionalQuantityInput(
                numerical_value=val,
                unit_string=speed_match.group(2).strip(),
            )

    # 8. Altitude
    alt: Optional[DimensionalQuantityInput] = None
    alt_match = re.search(r"(?:altitude|alt|at|cruising\s*at|flying\s*at|flight\s*level|fl)(?:\s*(?:of|is|:))?\s*(\d+(?:\.\d+)?)\s*(m|meter|meters|ft|feet)\b", text_lower)
    if not alt_match:
        alt_match = re.search(r"(\d+(?:\.\d+)?)\s*(m|meter|meters|ft|feet)\s*altitude\b", text_lower)
    if not alt_match:
        alt_match = re.search(r"sea\s*level\s*\((\d+)\s*(m|meter|meters|ft|feet)\)", text_lower)
    if not alt_match:
        alt_match = re.search(r"(?<!sq\s)(?<!sq)(?<!span\s)(?<!wingspan\s)\b(\d{3,5}(?:\.\d+)?)\s*(ft|feet)\b", text_lower)
    if alt_match:
        val = float(alt_match.group(1))
        alt = DimensionalQuantityInput(
            numerical_value=val,
            unit_string=alt_match.group(2).strip(),
        )
    elif any(
        kw in text_lower
        for kw in [
            "standard atmospheric conditions",
            "standard atmospheric condition",
            "standard atmosphere",
            "standard isa",
            "isa conditions",
            "isa sea-level",
            "isa defaults",
            "sea level",
            "sea-level",
            "0 m",
        ]
    ):
        alt = DimensionalQuantityInput(numerical_value=0.0, unit_string="m")

    # 9. CLmax
    clmax: Optional[float] = None
    clmax_match = re.search(r"(?:landing\s*clmax|clmax|cl_max)(?:\s*(?:of|is|:))?\s*(\d+(?:\.\d+)?)", text_lower)
    if clmax_match:
        clmax = float(clmax_match.group(1))

    # 10. Airfoil Thickness Ratio (t/c)
    tc_val: Optional[float] = None
    tc_match = re.search(r"(?:t/c|thickness(?:\s*to\s*chord)?(?:\s*ratio)?)(?:\s*(?:of|is|:))?\s*(\d+(?:\.\d+)?%?)", text_lower)
    if tc_match:
        raw_tc = tc_match.group(1)
        if "%" in raw_tc:
            tc_val = float(raw_tc.replace("%", "")) / 100.0
        else:
            v = float(raw_tc)
            tc_val = v / 100.0 if v > 1.0 else v

    # 11. Wing Sweep Angle (Lambda) in degrees
    sweep_val: Optional[float] = None
    sweep_match = re.search(r"(?:sweep(?:\s*angle)?|wing\s*sweep)(?:\s*(?:of|is|:))?\s*(\d+(?:\.\d+)?)\s*(?:deg|degrees|°)?", text_lower)
    if not sweep_match:
        sweep_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:deg|degrees|°)\s*(?:wing\s*)?sweep\b", text_lower)
    if sweep_match:
        sweep_val = float(sweep_match.group(1))

    # 12. Airfoil Technology Factor (kappa_A)
    tech_factor: Optional[float] = None
    if "supercritical" in text_lower:
        tech_factor = 0.95
    tech_match = re.search(r"(?:technology\s*factor|kappa_a|ka)(?:\s*(?:of|is|:))?\s*(\d+(?:\.\d+)?)", text_lower)
    if tech_match:
        tech_factor = float(tech_match.group(1))

    # 13. Standard ISA / Atmospheric defaults
    isa_assumed = False
    if any(
        kw in text_lower
        for kw in [
            "standard atmospheric conditions",
            "standard atmospheric condition",
            "standard atmosphere",
            "standard isa",
            "isa conditions",
            "isa sea-level",
            "isa defaults",
            "sea level",
            "sea-level",
            "standard conditions",
        ]
    ):
        isa_assumed = True
        if alt is None:
            alt = DimensionalQuantityInput(numerical_value=0.0, unit_string="m")

    return ExtractedTurnParameters(
        calculation_intent=intent,
        wingspan=span,
        wing_area=area,
        aircraft_mass=mass,
        passenger_count=pax,
        true_airspeed=speed,
        altitude=alt,
        maximum_lift_coefficient_clmax=clmax,
        airfoil_thickness_ratio=tc_val,
        wing_sweep_degrees=sweep_val,
        airfoil_technology_factor=tech_factor,
        confirmed_standard_isa_defaults=isa_assumed,
    )


def extract_parameters_llm_cloud(user_text: str) -> Optional[ExtractedTurnParameters]:
    """Extract parameters via Groq or Gemini cloud LLM with zero math and strict rate pacing."""
    user_text = normalize_text_commas(user_text)
    groq_key = os.getenv("GROQ_APIKEY") or os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("Gemini_APIKEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_APIKEY")

    system_prompt = (
        "You are an expert aerospace data extractor for AeroGuard-RAG.\n"
        "Extract raw numbers, raw unit strings, and calculation intent from user text.\n"
        "CRITICAL: If the user query asks conceptual, regulatory, airworthiness, standard, or explanatory questions without numerical sizing parameters, classify calculation_intent as 'regulatory_qa'.\n"
        "CRITICAL: NEVER perform math, calculations, unit conversions, or round numbers.\n"
        "Return JSON strictly matching this structure:\n"
        "{\n"
        '  "calculation_intent": "induced_drag" | "stall_speed" | "wing_loading" | "climb_gradient" | "static_margin" | "breguet_range" | "compressibility_correction" | "full_aerodynamic_audit" | "transonic_audit" | "regulatory_qa" | "out_of_scope",\n'
        '  "wingspan": {"numerical_value": float, "unit_string": string} | null,\n'
        '  "wing_area": {"numerical_value": float, "unit_string": string} | null,\n'
        '  "aircraft_mass": {"numerical_value": float, "unit_string": string} | null,\n'
        '  "passenger_count": int | null,\n'
        '  "true_airspeed": {"numerical_value": float, "unit_string": string} | null,\n'
        '  "altitude": {"numerical_value": float, "unit_string": string} | null,\n'
        '  "maximum_lift_coefficient_clmax": float | null,\n'
        '  "airfoil_thickness_ratio": float | null,\n'
        '  "wing_sweep_degrees": float | null,\n'
        '  "airfoil_technology_factor": float | null,\n'
        '  "confirmed_standard_isa_defaults": boolean\n'
        "}"
    )

    # 1. Try Groq (Primary)
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            time.sleep(0.3)  # Rate pacing for free-tier
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                model=os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile"),
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            raw_content = chat_completion.choices[0].message.content
            if raw_content:
                data = json.loads(raw_content)
                return ExtractedTurnParameters(**data)
        except Exception:
            pass  # Failover to Gemini

    # 2. Try Gemini (Fallback)
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(
                model_name=os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"),
                generation_config={"response_mime_type": "application/json", "temperature": 0.0},
                system_instruction=system_prompt,
            )
            time.sleep(0.3)
            response = model.generate_content(user_text)
            if response.text:
                data = json.loads(response.text)
                return ExtractedTurnParameters(**data)
        except Exception:
            pass

    return None


def extract_parameters(user_text: str, prefer_local: bool = False) -> ExtractedTurnParameters:
    """Unified extractor with prefer_local switch, cloud try, and deterministic fallback."""
    user_text = normalize_text_commas(user_text)
    if prefer_local:
        return extract_parameters_local_deterministic(user_text)

    extracted = extract_parameters_llm_cloud(user_text)
    if extracted is not None:
        return extracted
    return extract_parameters_local_deterministic(user_text)


def merge_turn_parameters(state: AircraftDesignState, turn_params: ExtractedTurnParameters) -> AircraftDesignState:
    """Non-destructively merge newly extracted turn parameters into persistent AircraftDesignState."""
    state.turn_index += 1

    if turn_params.calculation_intent is not None:
        state.calculation_intent = turn_params.calculation_intent

    if turn_params.wingspan is not None and turn_params.wingspan.numerical_value > 0.0:
        state.wingspan = turn_params.wingspan
    if turn_params.wing_area is not None and turn_params.wing_area.numerical_value > 0.0:
        state.wing_area = turn_params.wing_area
    if turn_params.aircraft_mass is not None and turn_params.aircraft_mass.numerical_value > 0.0:
        state.aircraft_mass = turn_params.aircraft_mass
    if turn_params.passenger_count is not None:
        state.passenger_count = turn_params.passenger_count
    if turn_params.true_airspeed is not None and turn_params.true_airspeed.numerical_value > 0.0:
        state.true_airspeed = turn_params.true_airspeed
    if turn_params.altitude is not None:
        state.altitude = turn_params.altitude
    if turn_params.maximum_lift_coefficient_clmax is not None:
        state.maximum_lift_coefficient_clmax = turn_params.maximum_lift_coefficient_clmax

    # Secondary parameters
    if turn_params.oswald_efficiency_factor is not None:
        state.oswald_efficiency_factor = turn_params.oswald_efficiency_factor
    if turn_params.zero_lift_drag_coefficient_cd0 is not None:
        state.zero_lift_drag_coefficient_cd0 = turn_params.zero_lift_drag_coefficient_cd0
    if turn_params.available_thrust is not None:
        state.available_thrust = turn_params.available_thrust
    if turn_params.center_of_gravity_position is not None:
        state.center_of_gravity_position = turn_params.center_of_gravity_position
    if turn_params.neutral_point_position is not None:
        state.neutral_point_position = turn_params.neutral_point_position
    if turn_params.mean_aerodynamic_chord is not None:
        state.mean_aerodynamic_chord = turn_params.mean_aerodynamic_chord
    if turn_params.fuel_mass is not None:
        state.fuel_mass = turn_params.fuel_mass
    if turn_params.propeller_efficiency is not None:
        state.propeller_efficiency = turn_params.propeller_efficiency
    if turn_params.specific_fuel_consumption is not None:
        state.specific_fuel_consumption = turn_params.specific_fuel_consumption
    if turn_params.incompressible_pressure_coefficient_cp0 is not None:
        state.incompressible_pressure_coefficient_cp0 = turn_params.incompressible_pressure_coefficient_cp0
    if turn_params.airfoil_thickness_ratio is not None:
        state.airfoil_thickness_ratio = turn_params.airfoil_thickness_ratio
    if turn_params.wing_sweep_degrees is not None:
        state.wing_sweep_degrees = turn_params.wing_sweep_degrees
    if turn_params.airfoil_technology_factor is not None:
        state.airfoil_technology_factor = turn_params.airfoil_technology_factor

    # Handle standard ISA sea level defaults
    if turn_params.confirmed_standard_isa_defaults or (state.altitude is not None and state.altitude.numerical_value == 0.0):
        if state.altitude is None:
            state.altitude = DimensionalQuantityInput(numerical_value=0.0, unit_string="m")
        if state.oswald_efficiency_factor is None or state.oswald_efficiency_factor == 0.80:
            state.oswald_efficiency_factor = 0.80

    return state


def inspect_boundary_conditions(state: AircraftDesignState) -> Tuple[bool, List[str]]:
    """Inspect AircraftDesignState against mandatory parameters for current intent."""
    if state.calculation_intent == "out_of_scope":
        state.pipeline_status = "OUT_OF_SCOPE_HALT"
        state.missing_parameters = []
        return False, []

    if state.calculation_intent == "regulatory_qa":
        state.pipeline_status = "READY_FOR_PHYSICS"
        state.missing_parameters = []
        return True, []

    config = load_schema_config()
    intent_map = config.get("intent_mandatory_parameters", {
        "induced_drag": ["wingspan", "wing_area", "aircraft_mass", "true_airspeed", "altitude"],
        "stall_speed": ["wing_area", "aircraft_mass", "altitude", "maximum_lift_coefficient_clmax"],
        "wing_loading": ["wing_area", "aircraft_mass"],
        "climb_gradient": ["wingspan", "wing_area", "aircraft_mass", "true_airspeed", "altitude", "available_thrust"],
        "static_margin": ["center_of_gravity_position", "neutral_point_position", "mean_aerodynamic_chord"],
        "breguet_range": ["wingspan", "wing_area", "aircraft_mass", "fuel_mass", "true_airspeed", "altitude", "propeller_efficiency", "specific_fuel_consumption"],
        "compressibility_correction": ["true_airspeed", "altitude", "incompressible_pressure_coefficient_cp0"],
        "full_aerodynamic_audit": ["wingspan", "wing_area", "aircraft_mass", "true_airspeed", "altitude", "maximum_lift_coefficient_clmax"],
        "transonic_audit": ["true_airspeed", "altitude"],
        "wing_sizing": ["wing_area", "aircraft_mass", "true_airspeed", "altitude"],
        "regulatory_qa": [],
    })

    intent = state.calculation_intent or "induced_drag"
    mandatory_fields = intent_map.get(intent, ["wing_area", "aircraft_mass", "true_airspeed", "altitude"])

    missing = []
    for field_name in mandatory_fields:
        val = getattr(state, field_name, None)
        if val is None:
            missing.append(field_name)
        elif field_name != "altitude" and isinstance(val, DimensionalQuantityInput) and val.numerical_value <= 0.0:
            missing.append(field_name)

    state.missing_parameters = missing
    if missing:
        state.pipeline_status = "HALTED_MISSING_PARAMS"
        return False, missing

    state.pipeline_status = "READY_FOR_PHYSICS"
    return True, []


def generate_counter_question(state: AircraftDesignState) -> str:
    """Generate precise engineering counter-question asking for missing parameters without guessing."""
    if not state.missing_parameters:
        return ""

    field_descriptions = {
        "wingspan": "Wing Span ($b$) [e.g., meters `m` or feet `ft`]",
        "wing_area": "Wing Planform Area ($S$) [e.g., `m^2` or `sq ft`]",
        "aircraft_mass": "Aircraft Gross Mass / Weight ($m$) [e.g., `kg` or `lbs`]",
        "true_airspeed": "Cruise True Airspeed ($V_\\infty$) [e.g., `m/s` or `knots`]",
        "altitude": "Flight Altitude ($h$) [e.g., `m` or `ft` — or confirm 'standard ISA sea-level']",
        "maximum_lift_coefficient_clmax": "Maximum Landing Lift Coefficient ($C_{L,\\max}$) [e.g., 1.50 - 1.80]",
        "available_thrust": "Available Engine Thrust ($T_{\\text{avail}}$) [e.g., `N` or `lbf`]",
        "center_of_gravity_position": "Center of Gravity position ($x_{cg}$) [e.g., `m`]",
        "neutral_point_position": "Aerodynamic Neutral Point ($x_{np}$) [e.g., `m`]",
        "mean_aerodynamic_chord": "Mean Aerodynamic Chord ($\\bar{c}$) [e.g., `m`]",
        "fuel_mass": "Fuel Mass ($m_f$) [e.g., `kg` or `lbs`]",
        "propeller_efficiency": "Propeller Efficiency factor ($\\eta_p$) [e.g., 0.82]",
        "specific_fuel_consumption": "Specific Fuel Consumption ($c_p$) [e.g., `1/s`]",
        "incompressible_pressure_coefficient_cp0": "Incompressible Pressure Coefficient ($C_{p,0}$)",
        "airfoil_thickness_ratio": "Airfoil Thickness-to-Chord Ratio ($t/c$) [e.g., 0.12 or 12%]",
        "wing_sweep_degrees": "Wing Sweep Angle ($\\Lambda$) [e.g., `25 deg`]",
        "airfoil_technology_factor": "Airfoil Technology Factor ($\\kappa_A$) [e.g., 0.87 (conventional) or 0.95 (supercritical)]",
    }

    bullet_points = []
    for idx, param in enumerate(state.missing_parameters, start=1):
        desc = field_descriptions.get(param, param.replace("_", " ").title())
        bullet_points.append(f"{idx}. **{desc}**")

    items_str = "\n".join(bullet_points)
    intent_label = (state.calculation_intent or "aerodynamic analysis").replace("_", " ").title()

    return (
        f"To perform a deterministic **{intent_label}** without guessing or hallucinating boundary conditions, "
        f"please provide the following required parameters:\n\n"
        f"{items_str}\n\n"
        f"*(Tip: You can also specify **'assume standard ISA sea-level conditions'** to automatically set altitude $h = 0\\text{{ m}}$ and Oswald efficiency $e = 0.80$.)*"
    )

