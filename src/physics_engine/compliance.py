"""Compliance evaluation and deterministic AeroSandbox parameter sweep advisor."""

from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pint

from src.gatekeeper.schemas import (
    AircraftDesignState,
    ComplianceReport,
    ComplianceStatusType,
    DesignAdvisory,
    PhysicsSolutionBundle,
    RuleCheckResult,
    SweepStepRecord,
)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "schemas_reference.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def evaluate_compliance(
    solution: PhysicsSolutionBundle,
    state: AircraftDesignState,
    regulatory_category: Optional[str] = None,
) -> ComplianceReport:
    """Evaluate aerodynamic metrics against FAA Part 23/25 thresholds and NASA heuristics."""
    category = regulatory_category or state.regulatory_category or "FAA_14_CFR_PART_23"
    rule_checks: List[RuleCheckResult] = []

    # 1. Stall Speed Check
    if solution.stall_speed_vs0_knots is not None:
        vs0 = solution.stall_speed_vs0_knots
        if category == "FAA_14_CFR_PART_23":
            if vs0 <= 58.0:
                status = "PASS"
            elif vs0 <= 61.0:
                status = "WARNING"
            else:
                status = "FAIL"
            rule_checks.append(
                RuleCheckResult(
                    rule_id="RULE-FAA-23-VS0",
                    metric_name="stall_speed_vs0_knots",
                    computed_value=vs0,
                    metric_unit="knots",
                    threshold_description="Vs0 <= 58 kts (Pass), 58-61 kts (Warning), > 61 kts (Fail)",
                    status=status,
                    regulation_reference="14 CFR § 23.2110 / § 23.49 (Landing stall speed limit <= 61 kts)",
                    source_document="14 CFR Part 23 (up to date as of 11-09-2026).pdf",
                )
            )
        else:  # Part 25
            if vs0 <= 135.0:
                status = "PASS"
            elif vs0 <= 145.0:
                status = "WARNING"
            else:
                status = "FAIL"
            rule_checks.append(
                RuleCheckResult(
                    rule_id="RULE-FAA-25-VS0",
                    metric_name="stall_speed_vs0_knots",
                    computed_value=vs0,
                    metric_unit="knots",
                    threshold_description="Vs0 <= 135 kts (Pass), 135-145 kts (Warning), > 145 kts (Fail)",
                    status=status,
                    regulation_reference="14 CFR § 25.103 Stall Speed & Approach Category Envelope",
                    source_document="14 CFR Part 25 (up to date as of 11-10-2026).pdf",
                )
            )

    # 2. Induced Drag Coefficient Check
    if solution.induced_drag_coefficient_cdi is not None:
        cdi = solution.induced_drag_coefficient_cdi
        target_cdi_pass = 0.040 if category == "FAA_14_CFR_PART_23" else 0.035
        target_cdi_warn = 0.065 if category == "FAA_14_CFR_PART_23" else 0.055
        if cdi <= target_cdi_pass:
            status = "PASS"
        elif cdi <= target_cdi_warn:
            status = "WARNING"
        else:
            status = "FAIL"
        rule_checks.append(
            RuleCheckResult(
                rule_id="RULE-NASA-CDI",
                metric_name="induced_drag_coefficient_cdi",
                computed_value=cdi,
                metric_unit="dimensionless",
                threshold_description=f"CDi <= {target_cdi_pass:.3f} (Pass), {target_cdi_pass:.3f}-{target_cdi_warn:.3f} (Warning), > {target_cdi_warn:.3f} (Fail)",
                status=status,
                regulation_reference="NASA SP-367 Ch. 4 Subsonic Induced Drag Efficiency",
                source_document="19760003955.pdf",
            )
        )

    # 3. Aspect Ratio Check
    if solution.aspect_ratio is not None:
        ar = solution.aspect_ratio
        target_ar_pass = 6.5 if category == "FAA_14_CFR_PART_23" else 7.0
        target_ar_warn = 5.0 if category == "FAA_14_CFR_PART_23" else 5.5
        if ar >= target_ar_pass:
            status = "PASS"
        elif ar >= target_ar_warn:
            status = "WARNING"
        else:
            status = "FAIL"
        rule_checks.append(
            RuleCheckResult(
                rule_id="RULE-NASA-AR",
                metric_name="aspect_ratio",
                computed_value=ar,
                metric_unit="dimensionless",
                threshold_description=f"AR >= {target_ar_pass:.1f} (Pass), {target_ar_warn:.1f}-{target_ar_pass:.1f} (Warning), < {target_ar_warn:.1f} (Fail)",
                status=status,
                regulation_reference="NASA SP-367 & FAA-H-8083-25C Ch. 5 Planform Design",
                source_document="19760003955.pdf",
            )
        )

    # 4. Static Margin Check (if provided)
    if solution.static_margin_fraction is not None:
        sm = solution.static_margin_fraction
        if 0.05 <= sm <= 0.25:
            status = "PASS"
        elif (0.02 <= sm < 0.05) or (0.25 < sm <= 0.35):
            status = "WARNING"
        else:
            status = "FAIL"
        rule_checks.append(
            RuleCheckResult(
                rule_id="RULE-FAA-SM",
                metric_name="static_margin_fraction",
                computed_value=sm,
                metric_unit="fraction_mac",
                threshold_description="0.05 <= SM <= 0.25 (Pass), 0.02-0.05 or 0.25-0.35 (Warning), <0.02 or >0.35 (Fail)",
                status=status,
                regulation_reference="14 CFR § 23.2135 Static Longitudinal Stability & NASA SP-367 Ch. 7",
                source_document="14 CFR Part 23 (up to date as of 11-09-2026).pdf",
            )
        )

    # 5. Steady Climb Gradient Check (if provided)
    if solution.climb_gradient_percent is not None:
        cgr = solution.climb_gradient_percent
        if cgr >= 8.33:
            status = "PASS"
        elif cgr >= 6.0:
            status = "WARNING"
        else:
            status = "FAIL"
        rule_checks.append(
            RuleCheckResult(
                rule_id="RULE-FAA-CGR",
                metric_name="climb_gradient_percent",
                computed_value=cgr,
                metric_unit="percent",
                threshold_description=">= 8.33% (Pass, 1:12 slope), 6.0%-8.33% (Warning), < 6.0% (Fail)",
                status=status,
                regulation_reference="14 CFR § 23.2120 Climb Requirements",
                source_document="14 CFR Part 23 (up to date as of 11-09-2026).pdf",
            )
        )

    # 6. Transonic Drag Divergence & Mach Number Check
    if solution.mach_number is not None and solution.drag_divergence_mach_number is not None:
        m_inf = solution.mach_number
        m_dd = solution.drag_divergence_mach_number
        m_cr = solution.critical_mach_number or (m_dd - 0.08)
        if m_inf <= m_cr:
            m_status = "PASS"
        elif m_inf <= m_dd:
            m_status = "WARNING"
        else:
            m_status = "FAIL"

        is_part25_or_high_speed = (category == "FAA_14_CFR_PART_25" or m_inf >= 0.50)
        reg_ref = (
            "14 CFR § 25.253 High-Speed Buffet Limits & NASA NTRS 20060008908"
            if is_part25_or_high_speed
            else "NASA SP-367 Ch. 5 Subsonic Screening"
        )
        src_doc = (
            "14 CFR Part 25 (up to date as of 11-10-2026).pdf"
            if is_part25_or_high_speed
            else "19760003955.pdf"
        )
        rule_checks.append(
            RuleCheckResult(
                rule_id="RULE-TRANSONIC-MDD",
                metric_name="mach_number",
                computed_value=round(m_inf, 4),
                metric_unit="Mach",
                threshold_description=f"M <= Mcr ({m_cr:.3f}) [Pass], Mcr < M <= Mdd ({m_dd:.3f}) [Warning], M > Mdd [Fail]",
                status=m_status,
                regulation_reference=reg_ref,
                source_document=src_doc,
            )
        )

    # 7. Transonic Wave Drag Coefficient Check
    if solution.wave_drag_coefficient_cdw is not None and solution.wave_drag_coefficient_cdw > 0.0:
        cdw = solution.wave_drag_coefficient_cdw
        if cdw == 0.0:
            w_status = "PASS"
        elif cdw <= 0.0020:
            w_status = "WARNING"
        else:
            w_status = "FAIL"
        rule_checks.append(
            RuleCheckResult(
                rule_id="RULE-NASA-CDW",
                metric_name="wave_drag_coefficient_cdw",
                computed_value=round(cdw, 6),
                metric_unit="dimensionless",
                threshold_description="CDw == 0.0000 (Pass), CDw <= 0.0020 (Warning), CDw > 0.0020 (Fail)",
                status=w_status,
                regulation_reference="NASA Transonic Drag Buildup (NTRS 20060008908) Wave Drag Criterion",
                source_document="20060008908.pdf",
            )
        )

    # Determine overall status using worst-case precedence
    overall_status: ComplianceStatusType = "PASS"
    statuses = [check.status for check in rule_checks]
    if "FAIL" in statuses:
        overall_status = "FAIL"
    elif "WARNING" in statuses:
        overall_status = "WARNING"
    elif not statuses:
        overall_status = "PASS"

    cert_desc = (
        "Normal / Commuter Category (<= 19 pax, <= 8,618 kg)"
        if category == "FAA_14_CFR_PART_23"
        else "Transport Category (> 19 pax or > 8,618 kg)"
    )

    # FR-13: Silent Advisor on PASS (unless calculation_intent == "wing_sizing")
    if overall_status == "PASS" and state.calculation_intent != "wing_sizing":
        return ComplianceReport(
            overall_status="PASS",
            regulatory_category=category,
            certification_level_description=cert_desc,
            rule_checks=rule_checks,
            design_advisory=None,
        )

    # FR-14: Conditional Parameter Sweep on WARNING or FAIL
    advisory = run_parameter_sweep_advisor(solution, state, category, rule_checks)

    return ComplianceReport(
        overall_status=overall_status,
        regulatory_category=category,
        certification_level_description=cert_desc,
        rule_checks=rule_checks,
        design_advisory=advisory,
    )


def run_parameter_sweep_advisor(
    solution: PhysicsSolutionBundle,
    state: AircraftDesignState,
    category: str,
    rule_checks: List[RuleCheckResult],
) -> Optional[DesignAdvisory]:
    """Execute deterministic parameter sweep in AeroSandbox to prescribe minimal compliant geometry."""
    failed_or_warn_rules = {check.metric_name: check for check in rule_checks if check.status in ("WARNING", "FAIL")}

    # Ensure SI-normalized values are always used (never raw DimensionalQuantityInput values)
    conv_map = {rec.parameter_name: rec.si_value for rec in state.unit_conversions}

    b0 = conv_map.get("wingspan")
    if b0 is None and state.wingspan is not None:
        from src.physics_engine.aero_solver import convert_quantity_to_si
        b0, _ = convert_quantity_to_si("wingspan", state.wingspan, "meter")

    s0 = conv_map.get("wing_area")
    if s0 is None and state.wing_area is not None:
        from src.physics_engine.aero_solver import convert_quantity_to_si
        s0, _ = convert_quantity_to_si("wing_area", state.wing_area, "meter ** 2")

    mass_val = conv_map.get("aircraft_mass")
    if mass_val is None and state.aircraft_mass is not None:
        from src.physics_engine.aero_solver import convert_quantity_to_si
        mass_val, _ = convert_quantity_to_si("aircraft_mass", state.aircraft_mass, "kilogram")
    q_pa = solution.dynamic_pressure_pascals or 0.0
    density = solution.air_density_kg_m3
    clmax = state.maximum_lift_coefficient_clmax or 1.60
    e = state.oswald_efficiency_factor

    # Target-Output Sizing Query: Solve optimal compliant wingspan
    if state.calculation_intent == "wing_sizing" and s0 is not None:
        target_ar = 7.5 if category == "FAA_14_CFR_PART_25" else 6.5
        target_cdi = 0.035 if category == "FAA_14_CFR_PART_25" else 0.040
        opt_b = math.sqrt(target_ar * s0)
        has_baseline_span = (b0 is not None and b0 > 0)
        delta_b = (opt_b - b0) if has_baseline_span else 0.0
        pct_change = (delta_b / b0 * 100.0) if has_baseline_span else 0.0
        orig_b = b0 if has_baseline_span else opt_b

        trajectory = []
        for step_idx, ar_val in enumerate([5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0]):
            b_val = math.sqrt(ar_val * s0)
            cl_val = solution.lift_coefficient_cl or 0.35
            cdi_val = (cl_val ** 2) / (math.pi * ar_val * e)
            di_n = q_pa * s0 * cdi_val
            vs0_kts = solution.stall_speed_vs0_knots or 0.0
            trajectory.append(
                SweepStepRecord(
                    step_index=step_idx,
                    swept_parameter_name="wingspan",
                    swept_parameter_value_si=round(b_val, 3),
                    computed_aspect_ratio=round(ar_val, 2),
                    computed_cdi=round(cdi_val, 6),
                    computed_induced_drag_newtons=round(di_n, 2),
                    computed_stall_speed_knots=round(vs0_kts, 2),
                    achieves_compliance=bool(ar_val >= target_ar and cdi_val <= target_cdi),
                )
            )

        summary = (
            f"Solved minimum compliant wingspan: {opt_b:.2f} m (AR = {target_ar:.1f}) "
            f"at planform area S = {s0:.2f} m²."
        )

        return DesignAdvisory(
            triggered_by_rule=f"{category} Wing Sizing & Aspect Ratio Heuristic (AR >= {target_ar:.1f})",
            swept_parameter_name="wingspan",
            original_value_si=round(orig_b, 3),
            recommended_value_si=round(opt_b, 3),
            unit_si="m",
            absolute_delta_si=round(delta_b, 3),
            percentage_change=round(pct_change, 1),
            projected_metric_name="aspect_ratio",
            projected_metric_value=target_ar,
            projected_metric_unit="dimensionless",
            within_thirty_percent_sweep_window=True,
            recommendation_summary=summary,
            sweep_trajectory=trajectory,
        )

    # Prioritize Stall Speed Violation sweep
    if "stall_speed_vs0_knots" in failed_or_warn_rules and b0 is not None and s0 is not None and mass_val is not None:
        target_vs0 = 61.0 if category == "FAA_14_CFR_PART_23" else 145.0
        pass_vs0 = 58.0 if category == "FAA_14_CFR_PART_23" else 135.0
        mean_chord0 = s0 / b0
        w_newtons = mass_val * 9.80665

        trajectory: List[SweepStepRecord] = []
        step_idx = 0
        step_delta = 0.20
        max_b = b0 * 1.30
        extended_max_b = b0 * 1.60

        curr_b = b0
        recommended_b = b0
        compliant_found = False

        while curr_b <= extended_max_b + 1e-6:
            curr_s = curr_b * mean_chord0
            curr_ar = (curr_b ** 2) / curr_s
            vs0_m_s = math.sqrt((2.0 * w_newtons) / (density * curr_s * clmax))
            vs0_kts = vs0_m_s / 0.5144444444444445
            cl_val = w_newtons / (q_pa * curr_s) if q_pa > 0 else 0.0
            cdi_val = (cl_val ** 2) / (math.pi * curr_ar * e) if curr_ar > 0 else 0.0
            di_n = q_pa * curr_s * cdi_val

            is_compliant = vs0_kts <= target_vs0
            trajectory.append(
                SweepStepRecord(
                    step_index=step_idx,
                    swept_parameter_name="wingspan",
                    swept_parameter_value_si=round(curr_b, 3),
                    computed_aspect_ratio=round(curr_ar, 3),
                    computed_cdi=round(cdi_val, 6),
                    computed_induced_drag_newtons=round(di_n, 2),
                    computed_stall_speed_knots=round(vs0_kts, 2),
                    achieves_compliance=is_compliant,
                )
            )

            if is_compliant and not compliant_found:
                compliant_found = True
                recommended_b = curr_b

            step_idx += 1
            curr_b += step_delta

        # If not compliant within sweep, choose the best achieved (extended_max_b) or calculate exact b
        exact_required_s = (2.0 * w_newtons) / (density * ((target_vs0 * 0.5144444444444445) ** 2) * clmax)
        exact_required_b = exact_required_s / mean_chord0
        if not compliant_found:
            recommended_b = exact_required_b

        within_30 = (recommended_b <= max_b)
        delta_b = recommended_b - b0
        pct_change = (delta_b / b0) * 100.0
        proj_vs0_m_s = math.sqrt((2.0 * w_newtons) / (density * (recommended_b * mean_chord0) * clmax))
        proj_vs0_kts = proj_vs0_m_s / 0.5144444444444445

        summary = (
            f"Stall speed exceeds regulatory limit ({solution.stall_speed_vs0_knots:.1f} kts > {target_vs0:.1f} kts). "
            f"Recommend increasing wingspan by {delta_b:.2f} m (+{pct_change:.1f}%) to {recommended_b:.2f} m "
            f"(with proportional planform area {recommended_b * mean_chord0:.2f} m²) to bring stall speed to {proj_vs0_kts:.1f} kts."
        )

        return DesignAdvisory(
            triggered_by_rule="FAA Part 23 Stall Speed Limit (Vs0 <= 61.0 kts)",
            swept_parameter_name="wingspan",
            original_value_si=round(b0, 3),
            recommended_value_si=round(recommended_b, 3),
            unit_si="m",
            absolute_delta_si=round(delta_b, 3),
            percentage_change=round(pct_change, 1),
            projected_metric_name="stall_speed_vs0_knots",
            projected_metric_value=round(proj_vs0_kts, 2),
            projected_metric_unit="knots",
            within_thirty_percent_sweep_window=within_30,
            recommendation_summary=summary,
            sweep_trajectory=trajectory[:15],
        )

    # Induced Drag or Aspect Ratio sweep
    if ("induced_drag_coefficient_cdi" in failed_or_warn_rules or "aspect_ratio" in failed_or_warn_rules) and b0 is not None and s0 is not None:
        target_cdi = 0.040 if category == "FAA_14_CFR_PART_23" else 0.035
        cl_val = solution.lift_coefficient_cl or 0.3
        vs0_kts = solution.stall_speed_vs0_knots or 0.0

        trajectory = []
        step_idx = 0
        step_delta = 0.20
        max_b = b0 * 1.30

        curr_b = b0
        recommended_b = b0
        compliant_found = False

        while curr_b <= max_b + 1e-6:
            curr_ar = (curr_b ** 2) / s0
            curr_cdi = (cl_val ** 2) / (math.pi * curr_ar * e)
            di_n = q_pa * s0 * curr_cdi
            is_compliant = curr_cdi <= target_cdi

            trajectory.append(
                SweepStepRecord(
                    step_index=step_idx,
                    swept_parameter_name="wingspan",
                    swept_parameter_value_si=round(curr_b, 3),
                    computed_aspect_ratio=round(curr_ar, 3),
                    computed_cdi=round(curr_cdi, 6),
                    computed_induced_drag_newtons=round(di_n, 2),
                    computed_stall_speed_knots=round(vs0_kts, 2),
                    achieves_compliance=is_compliant,
                )
            )
            if is_compliant and not compliant_found:
                compliant_found = True
                recommended_b = curr_b

            step_idx += 1
            curr_b += step_delta

        if not compliant_found:
            exact_ar = (cl_val ** 2) / (math.pi * target_cdi * e)
            recommended_b = math.sqrt(exact_ar * s0)

        within_30 = (recommended_b <= max_b)
        delta_b = recommended_b - b0
        pct_change = (delta_b / b0) * 100.0
        proj_ar = (recommended_b ** 2) / s0
        proj_cdi = (cl_val ** 2) / (math.pi * proj_ar * e)

        summary = (
            f"Induced drag coefficient CDi ({solution.induced_drag_coefficient_cdi:.4f}) exceeds target ({target_cdi:.3f}). "
            f"Recommend extending wingspan by {delta_b:.2f} m (+{pct_change:.1f}%) to {recommended_b:.2f} m at constant wing area "
            f"to raise Aspect Ratio to {proj_ar:.2f} and lower CDi to {proj_cdi:.4f}."
        )

        return DesignAdvisory(
            triggered_by_rule="Induced Drag Efficiency Heuristic (CDi <= 0.040)",
            swept_parameter_name="wingspan",
            original_value_si=round(b0, 3),
            recommended_value_si=round(recommended_b, 3),
            unit_si="m",
            absolute_delta_si=round(delta_b, 3),
            percentage_change=round(pct_change, 1),
            projected_metric_name="induced_drag_coefficient_cdi",
            projected_metric_value=round(proj_cdi, 5),
            projected_metric_unit="dimensionless",
            within_thirty_percent_sweep_window=within_30,
            recommendation_summary=summary,
            sweep_trajectory=trajectory[:15],
        )

    # Transonic Drag Divergence or Wave Drag sweep on Wing Sweep Angle (Lambda)
    if ("mach_number" in failed_or_warn_rules or "wave_drag_coefficient_cdw" in failed_or_warn_rules) and solution.mach_number is not None:
        sweep0 = state.wing_sweep_degrees or 0.0
        tc = state.airfoil_thickness_ratio or 0.12
        kappa_a = state.airfoil_technology_factor or 0.87
        cl_val = solution.lift_coefficient_cl or 0.0
        m_inf = solution.mach_number

        trajectory = []
        step_idx = 0
        step_delta = 1.0  # degrees
        max_sweep = min(45.0, max(sweep0 + 30.0, 40.0))

        curr_sweep = sweep0
        recommended_sweep = sweep0
        compliant_found = False

        while curr_sweep <= max_sweep + 1e-6:
            rad = math.radians(curr_sweep)
            cos_s = math.cos(rad)
            mdd_curr = (kappa_a / cos_s) - (tc / (cos_s ** 2)) - (0.10 * cl_val)
            cdw_curr = 20.0 * ((m_inf - mdd_curr) ** 4) if m_inf > mdd_curr else 0.0
            is_compliant = (m_inf <= mdd_curr)

            trajectory.append(
                SweepStepRecord(
                    step_index=step_idx,
                    swept_parameter_name="wing_sweep_degrees",
                    swept_parameter_value_si=round(curr_sweep, 1),
                    computed_aspect_ratio=round(solution.aspect_ratio or 0.0, 3),
                    computed_cdi=round(solution.induced_drag_coefficient_cdi or 0.0, 6),
                    computed_induced_drag_newtons=round(solution.induced_drag_force_newtons or 0.0, 2),
                    computed_stall_speed_knots=round(solution.stall_speed_vs0_knots or 0.0, 2),
                    achieves_compliance=is_compliant,
                )
            )
            if is_compliant and not compliant_found:
                compliant_found = True
                recommended_sweep = curr_sweep

            step_idx += 1
            curr_sweep += step_delta

        if not compliant_found:
            recommended_sweep = max_sweep

        delta_sweep = recommended_sweep - sweep0
        pct_change = (delta_sweep / sweep0 * 100.0) if sweep0 > 0 else (delta_sweep * 100.0)
        rad_rec = math.radians(recommended_sweep)
        cos_rec = math.cos(rad_rec)
        proj_mdd = (kappa_a / cos_rec) - (tc / (cos_rec ** 2)) - (0.10 * cl_val)
        proj_cdw = 20.0 * ((m_inf - proj_mdd) ** 4) if m_inf > proj_mdd else 0.0

        summary = (
            f"Cruise Mach ({m_inf:.3f}) exceeds drag divergence limit (M_dd = {solution.drag_divergence_mach_number:.3f}), "
            f"incurring wave drag CDw = {solution.wave_drag_coefficient_cdw or 0.0:.5f}. "
            f"Recommend increasing wing sweep angle from {sweep0:.1f}° to {recommended_sweep:.1f}° (+{delta_sweep:.1f}°) "
            f"to elevate M_dd to {proj_mdd:.3f} and eliminate transonic wave drag."
        )

        return DesignAdvisory(
            triggered_by_rule="Transonic Drag Divergence / Wave Drag Criterion",
            swept_parameter_name="wing_sweep_degrees",
            original_value_si=round(sweep0, 1),
            recommended_value_si=round(recommended_sweep, 1),
            unit_si="deg",
            absolute_delta_si=round(delta_sweep, 1),
            percentage_change=round(pct_change, 1),
            projected_metric_name="drag_divergence_mach_number",
            projected_metric_value=round(proj_mdd, 4),
            projected_metric_unit="Mach",
            within_thirty_percent_sweep_window=True,
            recommendation_summary=summary,
            sweep_trajectory=trajectory[:15],
        )

    return None

