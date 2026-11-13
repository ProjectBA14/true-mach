"""Acceptance test suite for AeroGuard-RAG executing TC-01 through TC-06 and regression suites."""

import json
from pathlib import Path
import pytest

from src.gatekeeper.schemas import AircraftDesignState
from src.orchestrator import process_user_turn

BENCHMARK_FILE = Path(__file__).resolve().parent / "benchmark_prompts.json"


@pytest.fixture
def benchmark_data():
    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_tc01_counter_questioning_gatekeeper_halt(benchmark_data):
    """TC-01: Incomplete query halts at gatekeeper and generates counter-question."""
    prompt = "Calculate the induced drag for my 4-seat prototype aircraft with a 10.5 m wingspan."
    state = AircraftDesignState(session_id="tc01-session")

    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is True
    assert result.state.pipeline_status == "HALTED_MISSING_PARAMS"
    assert result.state.calculation_intent == "induced_drag"
    assert "wing_area" in result.state.missing_parameters
    assert "aircraft_mass" in result.state.missing_parameters
    assert "true_airspeed" in result.state.missing_parameters
    assert "altitude" in result.state.missing_parameters
    assert result.solution is None
    assert "wing planform area" in result.assistant_chat_markdown.lower() or "wing_area" in result.assistant_chat_markdown.lower()


def test_tc02_multi_turn_state_retention(benchmark_data):
    """TC-02: Multi-turn state retention merges Turn 1 and Turn 2, then executes solver."""
    state = AircraftDesignState(session_id="tc02-session")

    # Turn 1
    t1_prompt = "Calculate the induced drag for my 4-seat prototype aircraft with a 10.5 m wingspan."
    r1 = process_user_turn(t1_prompt, state, prefer_local_extractor=True)
    assert r1.is_halted is True

    # Turn 2
    t2_prompt = "Wing area is 15.0 m^2, gross mass is 1100 kg, cruise airspeed is 60 m/s, and assume standard ISA sea-level conditions."
    r2 = process_user_turn(t2_prompt, r1.state, prefer_local_extractor=True)

    assert r2.is_halted is False
    assert r2.state.pipeline_status == "COMPLETED_VERIFIED"
    assert r2.state.regulatory_category == "FAA_14_CFR_PART_23"
    assert r2.solution is not None
    assert r2.solution.aspect_ratio == pytest.approx(7.35, rel=1e-3)
    assert r2.solution.lift_coefficient_cl == pytest.approx(0.32615, rel=1e-3)
    assert r2.solution.induced_drag_coefficient_cdi == pytest.approx(0.00576, rel=1e-2)
    assert r2.solution.induced_drag_force_newtons == pytest.approx(190.47, rel=1e-2)
    assert r2.compliance_report is not None
    assert r2.compliance_report.overall_status == "PASS"
    assert r2.compliance_report.design_advisory is None


def test_tc03_faa_part23_compliance_pass_silent_advisor(benchmark_data):
    """TC-03: FAA Part 23 PASS with strictly silent advisor."""
    prompt = (
        "Run a full aerodynamic and stall speed audit for a 4-passenger aircraft at sea level (0 m): "
        "wingspan 11.0 m, wing area 16.2 m^2, gross mass 1050 kg, cruise speed 62 m/s, and landing CLmax of 1.65."
    )
    state = AircraftDesignState(session_id="tc03-session")

    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.state.pipeline_status == "COMPLETED_VERIFIED"
    assert result.state.regulatory_category == "FAA_14_CFR_PART_23"
    assert result.solution is not None
    assert result.solution.stall_speed_vs0_knots == pytest.approx(48.765, abs=0.5)
    assert result.compliance_report.overall_status == "PASS"
    assert result.compliance_report.design_advisory is None


def test_tc04_faa_part23_compliance_fail_parameter_sweep(benchmark_data):
    """TC-04: FAA Part 23 FAIL (> 61 kts) triggers deterministic AeroSandbox parameter sweep."""
    prompt = (
        "Evaluate stall speed and induced drag compliance for a 6-passenger commuter aircraft at sea level (0 m) "
        "with wingspan 8.4 m, wing area 10.5 m^2, gross mass 1850 kg, cruise speed 52 m/s, and landing CLmax 1.35."
    )
    state = AircraftDesignState(session_id="tc04-session")

    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.state.pipeline_status == "COMPLETED_VERIFIED"
    assert result.state.regulatory_category == "FAA_14_CFR_PART_23"
    assert result.solution is not None
    assert result.solution.stall_speed_vs0_knots == pytest.approx(88.838, abs=0.5)
    assert result.compliance_report.overall_status == "FAIL"
    assert result.compliance_report.design_advisory is not None
    assert result.compliance_report.design_advisory.swept_parameter_name == "wingspan"
    assert len(result.compliance_report.design_advisory.sweep_trajectory) > 0


def test_tc04_mixed_unit_fail_parameter_sweep_regression():
    """Regression test (Issue 1): Mixed-unit FAIL inputs (ft, sq ft, lbs) produce positive, non-zero SI wingspan increase."""
    prompt = (
        "Evaluate stall speed and compliance for an aircraft with wingspan 27.5 ft, wing area 113 sq ft, "
        "gross weight 4078 lbs, cruise speed 101 knots, and landing CLmax 1.35 at sea level (0 m)."
    )
    state = AircraftDesignState(session_id="tc04-mixed-regression")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.state.pipeline_status == "COMPLETED_VERIFIED"
    assert result.compliance_report.overall_status == "FAIL"
    assert result.compliance_report.design_advisory is not None

    advisory = result.compliance_report.design_advisory
    assert advisory.swept_parameter_name == "wingspan"
    assert advisory.unit_si == "m"
    # Verify that SI-normalized values are used (~8.382 m, not raw 27.5 m)
    assert advisory.original_value_si == pytest.approx(8.382, abs=0.05)
    # Recommended span must be strictly greater than original, producing a positive, non-zero increase
    assert advisory.recommended_value_si > advisory.original_value_si
    assert advisory.absolute_delta_si > 0.0
    assert advisory.percentage_change > 0.0


def test_tc05_mixed_imperial_units_pint_conversion_part25(benchmark_data):
    """TC-05: Mixed Imperial/Aviation units converted via Pint and routed to Part 25."""
    prompt = (
        "Compute induced drag and wing loading for a 25-passenger regional transport aircraft with "
        "wingspan 95 ft, wing area 850 sq ft, gross weight 42000 lbs, flying at 220 knots at an altitude of 10000 ft."
    )
    state = AircraftDesignState(session_id="tc05-session")

    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.state.pipeline_status == "COMPLETED_VERIFIED"
    assert result.state.regulatory_category == "FAA_14_CFR_PART_25"
    assert result.solution is not None

    # Check Pint conversions
    conv_map = {rec.parameter_name: rec.si_value for rec in state.unit_conversions}
    assert conv_map["wingspan"] == pytest.approx(28.956, abs=0.01)
    assert conv_map["wing_area"] == pytest.approx(78.9676, abs=0.01)
    assert conv_map["aircraft_mass"] == pytest.approx(19050.88, abs=0.5)
    assert conv_map["true_airspeed"] == pytest.approx(113.178, abs=0.01)
    assert conv_map["altitude"] == pytest.approx(3048.0, abs=1.0)

    assert result.solution.aspect_ratio == pytest.approx(10.618, rel=1e-3)
    assert result.solution.induced_drag_force_newtons == pytest.approx(2857.4, rel=1e-2)
    assert result.compliance_report.overall_status == "PASS"


def test_tc06_out_of_scope_graceful_handling(benchmark_data):
    """TC-06: Out-of-scope orbital/materials query handled gracefully without hallucination."""
    prompt = (
        "Calculate the orbital Hohmann transfer delta-V for a geostationary communication satellite "
        "and check NASA structural titanium creep limits at 1400 Kelvin."
    )
    state = AircraftDesignState(session_id="tc06-session")

    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is True
    assert result.state.pipeline_status == "OUT_OF_SCOPE_HALT"
    assert result.state.calculation_intent == "out_of_scope"
    assert result.solution is None
    assert "out of aerodynamic scope" in result.assistant_chat_markdown.lower()


def test_regulatory_qa_standards_inquiry():
    """Issue 2 Verification: Conceptual regulatory questions trigger regulatory_qa without requiring numeric sizing parameters."""
    prompt = "What are the airworthiness standards for a normal plane?"
    state = AircraftDesignState(session_id="reg-qa-session")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.state.pipeline_status == "COMPLETED_VERIFIED"
    assert result.state.calculation_intent == "regulatory_qa"
    assert result.solution is None
    assert len(result.state.retrieved_citations) > 0
    assert "part 23" in result.assistant_chat_markdown.lower()
    assert "61 knots" in result.assistant_chat_markdown.lower()
    assert not result.state.missing_parameters


def test_regulatory_qa_normal_passenger_aircraft_regression():
    """Regression Test: 'Could explain all the standard that a normal passenger aircraft' routes to regulatory_qa with zero missing params."""
    prompt = "Could explain all the standard that a normal passenger aircraft"
    state = AircraftDesignState(session_id="reg-normal-passenger-aircraft-session")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.state.pipeline_status == "COMPLETED_VERIFIED"
    assert result.state.calculation_intent == "regulatory_qa"
    assert result.solution is None
    assert result.state.missing_parameters == []
    assert len(result.state.retrieved_citations) > 0
    assert "part 23" in result.assistant_chat_markdown.lower() or "standards" in result.assistant_chat_markdown.lower()


def test_target_output_wing_sizing_and_standard_atmosphere():
    """Target-Output Sizing Test: 'Assuming standard atmospheric conditions and 35 passengers, what would be the most applicable wingspan?'"""
    prompt = "Assuming standard atmospheric conditions and 35 passengers, what would be the most applicable wingspan?"
    state = AircraftDesignState(session_id="target-sizing-session")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is True
    assert result.state.pipeline_status == "HALTED_MISSING_PARAMS"
    assert result.state.calculation_intent == "wing_sizing"
    assert result.state.regulatory_category == "FAA_14_CFR_PART_25"

    # Assert altitude == 0.0 and NOT in missing_parameters
    assert result.state.altitude is not None
    assert result.state.altitude.numerical_value == 0.0
    assert "altitude" not in result.state.missing_parameters

    # Assert wingspan is NOT in missing_parameters (only wing_area, aircraft_mass, true_airspeed are requested)
    assert "wingspan" not in result.state.missing_parameters
    assert set(result.state.missing_parameters) == {"wing_area", "aircraft_mass", "true_airspeed"}


def test_target_output_wing_sizing_multi_turn_solve():
    """Target-Output Sizing Multi-Turn: Turn 2 supplies missing parameters and solves optimal wingspan."""
    state = AircraftDesignState(session_id="target-sizing-multiturn")

    # Turn 1
    t1_prompt = "Assuming standard atmospheric conditions and 35 passengers, what would be the most applicable wingspan?"
    r1 = process_user_turn(t1_prompt, state, prefer_local_extractor=True)
    assert r1.is_halted is True

    # Turn 2
    t2_prompt = "Wing area is 55.0 m^2, gross mass is 18000 kg, and cruise airspeed is 92 m/s."
    r2 = process_user_turn(t2_prompt, r1.state, prefer_local_extractor=True)

    assert r2.is_halted is False
    assert r2.state.pipeline_status == "COMPLETED_VERIFIED"
    assert r2.state.regulatory_category == "FAA_14_CFR_PART_25"
    assert r2.solution is not None
    assert r2.compliance_report is not None
    assert r2.compliance_report.design_advisory is not None
    advisory = r2.compliance_report.design_advisory
    assert advisory.swept_parameter_name == "wingspan"
    # Target AR = 7.5 -> b = sqrt(7.5 * 55.0) = ~20.31 m
    assert advisory.recommended_value_si == pytest.approx(20.31, abs=0.1)
    assert len(advisory.sweep_trajectory) > 0


def test_extraterrestrial_mars_flight_out_of_scope():
    """Issue 3 Verification: Non-Earth/planetary atmosphere queries halt with out_of_scope explaining Earth ISA scope."""
    prompt = "Calculate aerodynamic lift and drag for an autonomous exploration drone in the Martian atmosphere on Mars with a 2 m wingspan."
    state = AircraftDesignState(session_id="mars-session")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is True
    assert result.state.pipeline_status == "OUT_OF_SCOPE_HALT"
    assert result.state.calculation_intent == "out_of_scope"
    assert result.solution is None
    assert "extraterrestrial" in result.assistant_chat_markdown.lower() or "earth" in result.assistant_chat_markdown.lower()


def test_transonic_missing_boundary_condition_halt():
    """Phase 2 Verification: Transonic audit missing airspeed/altitude halts with counter-question."""
    prompt = "Run a transonic wave drag and drag divergence audit for a transport wing with 25 degrees sweep and 0.12 t/c."
    state = AircraftDesignState(session_id="transonic-halt-session")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is True
    assert result.state.pipeline_status == "HALTED_MISSING_PARAMS"
    assert result.state.calculation_intent == "transonic_audit"
    assert "true_airspeed" in result.state.missing_parameters
    assert "altitude" in result.state.missing_parameters
    assert result.solution is None
    assert "required parameters" in result.assistant_chat_markdown.lower()


def test_transonic_audit_subcritical_pass():
    """Phase 2 Verification: High-speed transport aircraft below drag divergence achieves compliance."""
    prompt = (
        "Run a transonic audit for a 150-passenger transport aircraft at altitude 10000 m: "
        "wingspan 34 m, wing area 122 m^2, gross mass 60000 kg, cruise airspeed 220 m/s, "
        "wing sweep 28 degrees, airfoil thickness ratio 0.11, and supercritical technology factor 0.95."
    )
    state = AircraftDesignState(session_id="transonic-pass-session")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.state.pipeline_status == "COMPLETED_VERIFIED"
    assert result.state.regulatory_category == "FAA_14_CFR_PART_25"
    assert result.solution is not None

    sol = result.solution
    assert sol.mach_number == pytest.approx(0.734, abs=0.02)
    assert sol.drag_divergence_mach_number is not None
    assert sol.drag_divergence_mach_number > sol.mach_number
    assert sol.wave_drag_coefficient_cdw == 0.0
    assert sol.prandtl_glauert_beta == pytest.approx(0.679, abs=0.03)

    # Citations check
    cit_ids = [c.citation_id for c in result.state.retrieved_citations]
    assert "FAA-14CFR-25-253" in cit_ids
    assert "FAA-AC-25-7D-CH2" in cit_ids
    assert "NASA-CR-20060008908" in cit_ids
    assert "NACA-R-1135-COMPRESSIBLE" in cit_ids


def test_transonic_audit_wave_drag_fail_parameter_sweep():
    """Phase 2 Verification: Transonic flight exceeding Mdd triggers wave drag FAIL and wing sweep sweep advisor."""
    prompt = (
        "Evaluate transonic wave drag and drag divergence for a transport aircraft at altitude 11000 m "
        "flying at Mach 0.82 with wing sweep 0 deg, airfoil thickness ratio 0.14, wingspan 30 m, "
        "wing area 100 m^2, gross mass 45000 kg, and conventional technology factor 0.87."
    )
    state = AircraftDesignState(session_id="transonic-fail-sweep-session")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.state.pipeline_status == "COMPLETED_VERIFIED"
    assert result.solution is not None

    sol = result.solution
    assert sol.mach_number == pytest.approx(0.82, abs=0.01)
    # Korn Mdd with 0 sweep and 0.14 tc is ~0.87 - 0.14 - 0.1*CL ~ 0.68 - 0.73
    assert sol.drag_divergence_mach_number < sol.mach_number
    # Wave drag should be positive and substantial
    assert sol.wave_drag_coefficient_cdw > 0.0001
    assert result.compliance_report.overall_status in ("WARNING", "FAIL")

    # Parameter sweep should recommend increasing wing sweep angle
    advisory = result.compliance_report.design_advisory
    assert advisory is not None
    assert advisory.swept_parameter_name == "wing_sweep_degrees"
    assert advisory.recommended_value_si > 0.0
    assert len(advisory.sweep_trajectory) > 0


def test_comma_formatted_transonic_part25_inputs():
    """Regression Test: Comma-separated numbers (75,000 kg, 35,000 ft, Mach 0.82) parse accurately into SI values."""
    prompt = (
        "Evaluate transonic drag for 75,000 kg aircraft at 35,000 ft flying at Mach 0.82 with 120 m^2 wing area and 25 deg sweep."
    )
    state = AircraftDesignState(session_id="comma-transonic-part25")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.state.pipeline_status == "COMPLETED_VERIFIED"
    assert result.state.regulatory_category == "FAA_14_CFR_PART_25"
    assert result.solution is not None

    conv_map = {rec.parameter_name: rec.si_value for rec in result.state.unit_conversions}
    assert conv_map["aircraft_mass"] == pytest.approx(75000.0, rel=1e-3)
    assert conv_map["altitude"] == pytest.approx(10668.0, abs=1.0)
    assert conv_map["wing_area"] == pytest.approx(120.0, abs=0.01)
    assert result.solution.mach_number == pytest.approx(0.82, abs=0.01)

    # Transonic Mach check on Part 25 should attach 14 CFR § 25.253
    mach_checks = [c for c in result.compliance_report.rule_checks if c.metric_name == "mach_number"]
    assert len(mach_checks) == 1
    assert "14 CFR § 25.253" in mach_checks[0].regulation_reference


def test_comma_formatted_mass_followup_and_clean_sizing_advisory():
    """Regression Test: Multi-turn sizing query parses '18,500 kg' accurately and phrases advisory cleanly."""
    state = AircraftDesignState(session_id="comma-mass-sizing")

    # Turn 1
    t1_prompt = "Assuming standard atmospheric conditions and 35 passengers, what would be the most applicable wingspan?"
    r1 = process_user_turn(t1_prompt, state, prefer_local_extractor=True)
    assert r1.is_halted is True
    assert "wingspan" not in r1.state.missing_parameters

    # Turn 2 with comma-formatted mass 18,500 kg
    t2_prompt = "Wing area is 55.0 m^2, gross mass is 18,500 kg, and cruise airspeed is 92 m/s."
    r2 = process_user_turn(t2_prompt, r1.state, prefer_local_extractor=True)

    assert r2.is_halted is False
    assert r2.state.pipeline_status == "COMPLETED_VERIFIED"
    assert r2.state.aircraft_mass.numerical_value == 18500.0
    conv_map = {rec.parameter_name: rec.si_value for rec in r2.state.unit_conversions}
    assert conv_map["aircraft_mass"] == pytest.approx(18500.0, rel=1e-3)
    assert r2.state.regulatory_category == "FAA_14_CFR_PART_25"

    advisory = r2.compliance_report.design_advisory
    assert advisory is not None
    # Advisory recommendation summary phrasing check
    assert "Solved minimum compliant wingspan:" in advisory.recommendation_summary
    assert "Swept wingspan from" not in advisory.recommendation_summary
    assert "+0.0%" not in r2.assistant_chat_markdown
    assert "Solved minimum compliant wingspan:" in r2.assistant_chat_markdown


def test_low_speed_part23_no_part25_mach_citation():
    """Regression Test: Low-speed Part 23 aircraft (M < 0.50) must not cite 14 CFR § 25.253."""
    prompt = (
        "Run a full aerodynamic and stall speed audit for a 4-passenger aircraft at sea level (0 m): "
        "wingspan 11.0 m, wing area 16.2 m^2, gross mass 1050 kg, cruise speed 62 m/s, and landing CLmax of 1.65."
    )
    state = AircraftDesignState(session_id="part23-lowspeed-mach")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.state.regulatory_category == "FAA_14_CFR_PART_23"
    assert result.solution.mach_number < 0.50

    for check in result.compliance_report.rule_checks:
        assert "14 CFR § 25.253" not in check.regulation_reference
        assert "14 CFR Part 25" not in check.source_document


def test_advice_formula_normally_used():
    """Regression Test 1: Conceptual / formula query routes to regulatory_qa without demanding inputs."""
    prompt = "A bit of advice on aerodynamic analysis whats the formula normally used?"
    state = AircraftDesignState(session_id="advice-formula")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.state.calculation_intent == "regulatory_qa"
    assert result.state.missing_parameters == []
    assert result.is_halted is False
    assert "C_{Di}" in result.assistant_chat_markdown or "Induced Drag" in result.assistant_chat_markdown
    assert "V_{s0}" in result.assistant_chat_markdown or "Stall Speed" in result.assistant_chat_markdown


def test_single_metric_vs0_part23_cross_verification():
    """Regression Test 2: Single-metric verification evaluates Vs0 = 64 kts vs Part 23 <= 61 kts -> FAIL."""
    prompt = "I got Vs0 = 64 kts for a 6-seater—does that pass Part 23?"
    state = AircraftDesignState(session_id="single-metric-vs0")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.compliance_report is not None
    assert result.compliance_report.overall_status == "FAIL"
    assert result.compliance_report.regulatory_category == "FAA_14_CFR_PART_23"
    assert result.state.missing_parameters == []
    assert len(result.compliance_report.rule_checks) >= 1
    assert result.compliance_report.rule_checks[0].computed_value == 64.0
    assert result.compliance_report.rule_checks[0].status == "FAIL"
    assert "61" in result.assistant_chat_markdown
    assert "23.2110" in result.assistant_chat_markdown or "23.49" in result.assistant_chat_markdown


def test_category_check_19500_lbs_18_pax():
    """Regression Test 3: Weight > 19,000 lbs classifies as Part 25 despite 18 passengers."""
    prompt = "Is 19,500 lbs with 18 passengers Part 23 or Part 25?"
    state = AircraftDesignState(session_id="category-check-19500")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.state.regulatory_category == "FAA_14_CFR_PART_25"
    assert result.state.missing_parameters == []
    assert "Part 25" in result.assistant_chat_markdown
    assert "19,000" in result.assistant_chat_markdown


def test_isa_atmospheric_lookup_35000_ft():
    """Regression Test 4: ISA atmospheric lookup at 35,000 ft computes density and speed of sound."""
    prompt = "What is the ISA air density and speed of sound at 35,000 ft?"
    state = AircraftDesignState(session_id="isa-lookup-35000")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is False
    assert result.solution is not None
    assert result.solution.air_density_kg_m3 == pytest.approx(0.38, abs=0.02)
    assert result.solution.speed_of_sound_m_s == pytest.approx(297.86, abs=5.0)
    assert result.state.missing_parameters == []
    assert "Air Density" in result.assistant_chat_markdown
    assert "Speed of Sound" in result.assistant_chat_markdown


def test_airspeed_overwrite_not_reusing_prior():
    """Regression Test 5: Standalone airspeed inquiry does not reuse prior turn's airspeed."""
    state = AircraftDesignState(session_id="speed-overwrite-session")

    # Turn 1: Cessna flight condition (62 m/s)
    t1_prompt = (
        "Run a full aerodynamic and stall speed audit for a 4-passenger aircraft at sea level (0 m): "
        "wingspan 11.0 m, wing area 16.2 m^2, gross mass 1050 kg, cruise speed 62 m/s, and landing CLmax of 1.65."
    )
    r1 = process_user_turn(t1_prompt, state, prefer_local_extractor=True)
    assert r1.is_halted is False
    assert r1.state.true_airspeed.numerical_value == 62.0

    # Turn 2: Standalone high-speed inquiry
    t2_prompt = "380 knots true airspeed at 25,000 ft"
    r2 = process_user_turn(t2_prompt, r1.state, prefer_local_extractor=True)

    assert r2.is_halted is False
    assert r2.state.true_airspeed.numerical_value == 380.0
    assert r2.solution is not None
    # 380 kts at 25,000 ft is M ~ 0.63 (if 62 m/s were reused, M would be ~ 0.20)
    assert r2.solution.mach_number == pytest.approx(0.63, abs=0.02)


def test_negative_wingspan_domain_error():
    """Regression Test 6: Negative input values trigger DOMAIN_ERROR halt."""
    prompt = "Calculate induced drag for an aircraft with -12 m wingspan, 16 m^2 wing area, 1200 kg gross mass, 60 m/s cruise speed at 0 m altitude."
    state = AircraftDesignState(session_id="domain-error-negative-wingspan")
    result = process_user_turn(prompt, state, prefer_local_extractor=True)

    assert result.is_halted is True
    assert result.state.pipeline_status == "DOMAIN_ERROR"
    assert "Domain Error" in result.assistant_chat_markdown or "strictly positive" in result.assistant_chat_markdown


def test_multiturn_increase_wing_area():
    """Regression Test 7: Multi-turn 'increase the wing area to 18.5 m^2' updates parameter and recalculates."""
    state = AircraftDesignState(session_id="multiturn-area-increase")

    # Turn 1: Cessna
    t1_prompt = (
        "Run a full aerodynamic and stall speed audit for a 4-passenger aircraft at sea level (0 m): "
        "wingspan 11.0 m, wing area 16.2 m^2, gross mass 1050 kg, cruise speed 62 m/s, and landing CLmax of 1.65."
    )
    r1 = process_user_turn(t1_prompt, state, prefer_local_extractor=True)
    assert r1.is_halted is False
    assert r1.solution.stall_speed_vs0_knots == pytest.approx(48.75, abs=0.5)

    # Turn 2: Increase wing area to 18.5 m^2
    t2_prompt = "increase the wing area to 18.5 m^2"
    r2 = process_user_turn(t2_prompt, r1.state, prefer_local_extractor=True)

    assert r2.is_halted is False
    assert r2.state.wing_area.numerical_value == 18.5
    assert r2.state.wingspan.numerical_value == 11.0
    assert r2.state.aircraft_mass.numerical_value == 1050.0
    # Recalculated Vs0 drops from 48.75 kts to ~ 45.62 kts
    assert r2.solution.stall_speed_vs0_knots == pytest.approx(45.6, abs=0.5)


