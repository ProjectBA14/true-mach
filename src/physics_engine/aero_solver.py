"""Deterministic aerodynamic physics engine using AeroSandbox, SymPy, and Pint."""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
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


class AerodynamicDomainError(ValueError):
    """Raised when an aerodynamic parameter is outside physically plausible or valid domains."""
    pass


def convert_quantity_to_si(
    parameter_name: str,
    quantity_input: DimensionalQuantityInput,
    target_si_unit: str,
) -> Tuple[float, UnitConversionRecord]:
    """Convert user dimensional quantity into strict SI base units using Pint."""
    normalized_unit = quantity_input.unit_string.strip().lower()
    unit_aliases = {
        "kts": "knot",
        "knots": "knot",
        "kt": "knot",
        "sqm": "meter ** 2",
        "m^2": "meter ** 2",
        "m2": "meter ** 2",
        "sq ft": "foot ** 2",
        "sqft": "foot ** 2",
        "ft^2": "foot ** 2",
        "ft2": "foot ** 2",
        "lbs": "pound",
        "lb": "pound",
        "lbf": "pound_force",
        "ft": "foot",
        "feet": "foot",
        "m": "meter",
        "meter": "meter",
        "meters": "meter",
        "m/s": "meter / second",
        "mps": "meter / second",
        "kg": "kilogram",
        "kilograms": "kilogram",
        "newton": "newton",
        "newtons": "newton",
        "n": "newton",
        "pa": "pascal",
        "pascals": "pascal",
        "k": "kelvin",
        "kelvin": "kelvin",
    }
    resolved_unit = unit_aliases.get(normalized_unit, normalized_unit)
    pint_quantity = UNIT_REGISTRY.Quantity(quantity_input.numerical_value, resolved_unit)

    # Handle weight-to-mass conversion if user supplied force units (N or lbf) for mass
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


def solve_aerodynamics(state: AircraftDesignState) -> Tuple[PhysicsSolutionBundle, List[UnitConversionRecord]]:
    """Deterministically solve aerodynamic properties using AeroSandbox, SymPy, and Pint."""
    unit_conversions: List[UnitConversionRecord] = []

    # 1. SI Unit Normalization
    wing_area_m2: Optional[float] = None
    if state.wing_area is not None:
        wing_area_m2, rec = convert_quantity_to_si("wing_area", state.wing_area, "meter ** 2")
        unit_conversions.append(rec)
        if wing_area_m2 <= 0.0:
            raise AerodynamicDomainError(f"Wing area must be strictly positive (got {wing_area_m2} m²).")

    wingspan_m: Optional[float] = None
    if state.wingspan is not None:
        wingspan_m, rec = convert_quantity_to_si("wingspan", state.wingspan, "meter")
        unit_conversions.append(rec)
        if wingspan_m <= 0.0:
            raise AerodynamicDomainError(f"Wingspan must be strictly positive (got {wingspan_m} m).")
    elif state.calculation_intent == "wing_sizing" and wing_area_m2 is not None:
        target_ar = 7.5 if state.regulatory_category == "FAA_14_CFR_PART_25" else 6.5
        wingspan_m = math.sqrt(target_ar * wing_area_m2)

    mass_kg: Optional[float] = None
    if state.aircraft_mass is not None:
        mass_kg, rec = convert_quantity_to_si("aircraft_mass", state.aircraft_mass, "kilogram")
        unit_conversions.append(rec)
        if mass_kg <= 0.0:
            raise AerodynamicDomainError(f"Aircraft mass must be strictly positive (got {mass_kg} kg).")

    altitude_m: float = 0.0
    if state.altitude is not None:
        altitude_m, rec = convert_quantity_to_si("altitude", state.altitude, "meter")
        unit_conversions.append(rec)
    if altitude_m < -500.0 or altitude_m > 20000.0:
        raise AerodynamicDomainError(f"Altitude {altitude_m} m is outside the valid troposphere/stratosphere model (-500 m to 20,000 m).")

    # 2. Atmosphere using AeroSandbox
    atmo = asb.Atmosphere(altitude=altitude_m)
    density = float(atmo.density())
    pressure = float(atmo.pressure())
    temperature = float(atmo.temperature())
    speed_of_sound = float(atmo.speed_of_sound())

    dynamic_viscosity = 1.789e-5 * ((temperature / 288.15) ** 1.5) * (288.15 + 110.4) / (temperature + 110.4)

    true_airspeed_m_s: Optional[float] = None
    if state.true_airspeed is not None:
        if state.true_airspeed.unit_string.lower().strip() == "mach":
            true_airspeed_m_s = state.true_airspeed.numerical_value * speed_of_sound
            unit_conversions.append(
                UnitConversionRecord(
                    parameter_name="true_airspeed",
                    input_value=state.true_airspeed.numerical_value,
                    input_unit="mach",
                    si_value=round(true_airspeed_m_s, 6),
                    si_unit="meter / second",
                )
            )
        else:
            true_airspeed_m_s, rec = convert_quantity_to_si("true_airspeed", state.true_airspeed, "meter / second")
            unit_conversions.append(rec)
        if true_airspeed_m_s <= 0.0:
            raise AerodynamicDomainError(f"True airspeed must be strictly positive (got {true_airspeed_m_s} m/s).")

    # 3. Derived quantities and SymPy traces
    equation_traces: List[EquationTrace] = []

    # Weight
    weight_n: Optional[float] = None
    if mass_kg is not None:
        weight_n = mass_kg * STANDARD_GRAVITY_M_S2
        m_sym, g_sym = sp.symbols("m g")
        W_expr = m_sym * g_sym
        equation_traces.append(
            EquationTrace(
                equation_name="Aircraft Weight",
                symbolic_latex=sp.latex(sp.Eq(sp.Symbol("W"), W_expr)),
                substituted_latex=f"W = {mass_kg:.2f} \\times {STANDARD_GRAVITY_M_S2:.5f} = {weight_n:.2f}\\text{{ N}}",
                output_variable_name="weight_newtons",
                output_value_si=round(weight_n, 4),
                output_unit_si="N",
                source_citation_id="NASA-SP-367-CH3",
            )
        )

    # Dynamic pressure
    dynamic_pressure_pa: Optional[float] = None
    if true_airspeed_m_s is not None:
        dynamic_pressure_pa = 0.5 * density * (true_airspeed_m_s ** 2)
        rho_sym, V_sym = sp.symbols(r"\rho V_\infty")
        q_expr = sp.Rational(1, 2) * rho_sym * (V_sym ** 2)
        equation_traces.append(
            EquationTrace(
                equation_name="Dynamic Pressure",
                symbolic_latex=sp.latex(sp.Eq(sp.Symbol(r"q_\infty"), q_expr)),
                substituted_latex=f"q_\\infty = \\frac{{1}}{{2}} \\times {density:.4f} \\times ({true_airspeed_m_s:.2f})^2 = {dynamic_pressure_pa:.2f}\\text{{ Pa}}",
                output_variable_name="dynamic_pressure_pascals",
                output_value_si=round(dynamic_pressure_pa, 4),
                output_unit_si="Pa",
                source_citation_id="NASA-SP-367-CH3",
            )
        )

    # Aspect ratio
    aspect_ratio: Optional[float] = None
    if wingspan_m is not None and wing_area_m2 is not None:
        aspect_ratio = (wingspan_m ** 2) / wing_area_m2
        b_sym, S_sym = sp.symbols("b S")
        AR_expr = (b_sym ** 2) / S_sym
        equation_traces.append(
            EquationTrace(
                equation_name="Aspect Ratio",
                symbolic_latex=sp.latex(sp.Eq(sp.Symbol("AR"), AR_expr)),
                substituted_latex=f"AR = \\frac{{({wingspan_m:.2f})^2}}{{{wing_area_m2:.2f}}} = {aspect_ratio:.4f}",
                output_variable_name="aspect_ratio",
                output_value_si=round(aspect_ratio, 6),
                output_unit_si="dimensionless",
                source_citation_id="NASA-SP-367-CH4",
            )
        )

    # Wing loading
    wing_loading_n_m2: Optional[float] = None
    wing_loading_kg_m2: Optional[float] = None
    if mass_kg is not None and wing_area_m2 is not None:
        wing_loading_kg_m2 = mass_kg / wing_area_m2
        if weight_n is not None:
            wing_loading_n_m2 = weight_n / wing_area_m2
            equation_traces.append(
                EquationTrace(
                    equation_name="Wing Loading",
                    symbolic_latex=r"\frac{W}{S} = \frac{m \cdot g_0}{S}",
                    substituted_latex=f"\\frac{{W}}{{S}} = \\frac{{{weight_n:.2f}}}{{{wing_area_m2:.2f}}} = {wing_loading_n_m2:.2f}\\text{{ N/m}}^2",
                    output_variable_name="wing_loading_n_m2",
                    output_value_si=round(wing_loading_n_m2, 4),
                    output_unit_si="N/m^2",
                    secondary_display_value=round(wing_loading_kg_m2, 2),
                    secondary_display_unit="kg/m^2",
                    source_citation_id="FAA-H-8083-25C-CH5",
                )
            )

    # Lift coefficient
    cl: Optional[float] = None
    if weight_n is not None and dynamic_pressure_pa is not None and wing_area_m2 is not None:
        cl = weight_n / (dynamic_pressure_pa * wing_area_m2)
        equation_traces.append(
            EquationTrace(
                equation_name="Lift Coefficient (Level Flight)",
                symbolic_latex=r"C_L = \frac{W}{q_\infty \cdot S}",
                substituted_latex=f"C_L = \\frac{{{weight_n:.2f}}}{{{dynamic_pressure_pa:.2f} \\times {wing_area_m2:.2f}}} = {cl:.5f}",
                output_variable_name="lift_coefficient_cl",
                output_value_si=round(cl, 6),
                output_unit_si="dimensionless",
                source_citation_id="NASA-SP-367-CH3",
            )
        )

    # Induced drag coefficient and force
    cdi: Optional[float] = None
    di_newtons: Optional[float] = None
    if cl is not None and aspect_ratio is not None:
        e = state.oswald_efficiency_factor
        cdi = (cl ** 2) / (math.pi * aspect_ratio * e)
        equation_traces.append(
            EquationTrace(
                equation_name="Induced Drag Coefficient",
                symbolic_latex=r"C_{Di} = \frac{C_L^2}{\pi \cdot AR \cdot e}",
                substituted_latex=f"C_{{Di}} = \\frac{{({cl:.5f})^2}}{{\\pi \\times {aspect_ratio:.4f} \\times {e:.2f}}} = {cdi:.6f}",
                output_variable_name="induced_drag_coefficient_cdi",
                output_value_si=round(cdi, 6),
                output_unit_si="dimensionless",
                source_citation_id="NASA-SP-367-CH4",
            )
        )
        if dynamic_pressure_pa is not None and wing_area_m2 is not None:
            di_newtons = dynamic_pressure_pa * wing_area_m2 * cdi
            equation_traces.append(
                EquationTrace(
                    equation_name="Induced Drag Force",
                    symbolic_latex=r"D_i = q_\infty \cdot S \cdot C_{Di}",
                    substituted_latex=f"D_i = {dynamic_pressure_pa:.2f} \\times {wing_area_m2:.2f} \\times {cdi:.6f} = {di_newtons:.2f}\\text{{ N}}",
                    output_variable_name="induced_drag_force_newtons",
                    output_value_si=round(di_newtons, 4),
                    output_unit_si="N",
                    source_citation_id="NASA-SP-367-CH4",
                )
            )

    # Mach number, Prandtl-Glauert, Korn Mdd, and Wave Drag
    mach: Optional[float] = None
    prandtl_beta: Optional[float] = None
    prandtl_glauert_cp: Optional[float] = None
    m_cr: Optional[float] = None
    m_dd: Optional[float] = None
    cdw: Optional[float] = None
    dw_newtons: Optional[float] = None

    if true_airspeed_m_s is not None:
        mach = true_airspeed_m_s / speed_of_sound
        if mach >= 1.0:
            raise AerodynamicDomainError(f"Mach number {mach:.3f} >= 1.0: Subsonic and transonic aerodynamics formulas invalid for supersonic flow.")

        prandtl_beta = math.sqrt(max(1e-6, 1.0 - (mach ** 2)))

        # SymPy trace for Mach number
        M_sym, V_sym, a_sym = sp.symbols(r"M_\infty V_\infty a")
        mach_eq = sp.Eq(M_sym, V_sym / a_sym)
        equation_traces.append(
            EquationTrace(
                equation_name="Mach Number",
                symbolic_latex=sp.latex(mach_eq),
                substituted_latex=f"M_\\infty = \\frac{{{true_airspeed_m_s:.2f}\\text{{ m/s}}}}{{{speed_of_sound:.2f}\\text{{ m/s}}}} = {mach:.4f}",
                output_variable_name="mach_number",
                output_value_si=round(mach, 4),
                output_unit_si="dimensionless",
                source_citation_id="NASA-SP-367-CH3",
            )
        )

        # SymPy trace for Prandtl-Glauert compressibility factor
        beta_sym = sp.Symbol(r"\beta")
        beta_eq = sp.Eq(beta_sym, sp.sqrt(1 - M_sym**2))
        equation_traces.append(
            EquationTrace(
                equation_name="Prandtl-Glauert Compressibility Factor",
                symbolic_latex=sp.latex(beta_eq),
                substituted_latex=f"\\beta = \\sqrt{{1 - ({mach:.4f})^2}} = {prandtl_beta:.4f}",
                output_variable_name="prandtl_glauert_beta",
                output_value_si=round(prandtl_beta, 4),
                output_unit_si="dimensionless",
                source_citation_id="NACA-R-1135",
            )
        )

        if state.incompressible_pressure_coefficient_cp0 is not None:
            if 0.30 <= mach < 0.85:
                prandtl_glauert_cp = state.incompressible_pressure_coefficient_cp0 / prandtl_beta
                equation_traces.append(
                    EquationTrace(
                        equation_name="Prandtl-Glauert Corrected Pressure Coefficient",
                        symbolic_latex=r"C_{p,\text{comp}} = \frac{C_{p,0}}{\sqrt{1 - M_\infty^2}}",
                        substituted_latex=f"C_{{p,\\text{{comp}}}} = \\frac{{{state.incompressible_pressure_coefficient_cp0:.4f}}}{{{prandtl_beta:.4f}}} = {prandtl_glauert_cp:.4f}",
                        output_variable_name="prandtl_glauert_cp_corrected",
                        output_value_si=round(prandtl_glauert_cp, 4),
                        output_unit_si="dimensionless",
                        source_citation_id="NACA-R-1135",
                    )
                )

        # Korn Drag Divergence Mach & Wave Drag
        sweep_deg = state.wing_sweep_degrees if state.wing_sweep_degrees is not None else 0.0
        sweep_rad = math.radians(sweep_deg)
        cos_sweep = math.cos(sweep_rad)
        tc = state.airfoil_thickness_ratio if state.airfoil_thickness_ratio is not None else 0.12
        kappa_a = state.airfoil_technology_factor if state.airfoil_technology_factor is not None else 0.87
        cl_for_korn = cl if cl is not None else 0.0

        # Korn Equation: M_dd = kappa_a / cos(sweep) - (t/c) / cos^2(sweep) - 0.10 * C_L
        m_dd = (kappa_a / cos_sweep) - (tc / (cos_sweep ** 2)) - (0.10 * cl_for_korn)
        m_cr = m_dd - 0.08

        # Wave drag buildup (Mason / Lock empirical formulation)
        if mach > m_dd:
            cdw = 20.0 * ((mach - m_dd) ** 4)
        else:
            cdw = 0.0

        if dynamic_pressure_pa is not None and wing_area_m2 is not None:
            dw_newtons = dynamic_pressure_pa * wing_area_m2 * cdw

        equation_traces.append(
            EquationTrace(
                equation_name="Korn Drag Divergence Mach Number",
                symbolic_latex=r"M_{dd} = \frac{\kappa_A}{\cos \Lambda} - \frac{t/c}{\cos^2 \Lambda} - 0.10 \cdot C_L",
                substituted_latex=f"M_{{dd}} = \\frac{{{kappa_a:.2f}}}{{\\cos({sweep_deg:.1f}^\\circ)}} - \\frac{{{tc:.3f}}}{{\\cos^2({sweep_deg:.1f}^\\circ)}} - 0.10 \\times {cl_for_korn:.3f} = {m_dd:.4f}",
                output_variable_name="drag_divergence_mach_number",
                output_value_si=round(m_dd, 4),
                output_unit_si="dimensionless",
                secondary_display_value=round(m_cr, 4),
                secondary_display_unit="M_cr",
                source_citation_id="NASA-CR-20060008908",
            )
        )

        if cdw > 0.0:
            equation_traces.append(
                EquationTrace(
                    equation_name="Transonic Wave Drag Coefficient (Lock Buildup)",
                    symbolic_latex=r"C_{Dw} = 20 \cdot (M_\infty - M_{dd})^4",
                    substituted_latex=f"C_{{Dw}} = 20 \\times ({mach:.4f} - {m_dd:.4f})^4 = {cdw:.6f}",
                    output_variable_name="wave_drag_coefficient_cdw",
                    output_value_si=round(cdw, 6),
                    output_unit_si="dimensionless",
                    source_citation_id="NASA-CR-20060008908",
                )
            )

    # Total drag & Lift-to-Drag
    cd: Optional[float] = None
    d_total_newtons: Optional[float] = None
    ld_ratio: Optional[float] = None
    if cdi is not None or cdw is not None:
        cd0 = state.zero_lift_drag_coefficient_cd0
        cd = cd0 + (cdi if cdi is not None else 0.0) + (cdw if cdw is not None else 0.0)
        if dynamic_pressure_pa is not None and wing_area_m2 is not None:
            d_total_newtons = dynamic_pressure_pa * wing_area_m2 * cd
        if cl is not None and cd > 0:
            ld_ratio = cl / cd

    # Stall speed
    vs0_m_s: Optional[float] = None
    vs0_knots: Optional[float] = None
    if weight_n is not None and wing_area_m2 is not None and state.maximum_lift_coefficient_clmax is not None:
        clmax = state.maximum_lift_coefficient_clmax
        vs0_m_s = math.sqrt((2.0 * weight_n) / (density * wing_area_m2 * clmax))
        vs0_knots = float(UNIT_REGISTRY.Quantity(vs0_m_s, "meter / second").to("knot").magnitude)
        equation_traces.append(
            EquationTrace(
                equation_name="Landing Stall Speed (Vs0)",
                symbolic_latex=r"V_{s0} = \sqrt{\frac{2 W}{\rho \cdot S \cdot C_{L,\max}}}",
                substituted_latex=f"V_{{s0}} = \\sqrt{{\\frac{{2 \\times {weight_n:.2f}}}{{{density:.4f} \\times {wing_area_m2:.2f} \\times {clmax:.2f}}}}} = {vs0_m_s:.3f}\\text{{ m/s}} = {vs0_knots:.3f}\\text{{ kts}}",
                output_variable_name="stall_speed_vs0_knots",
                output_value_si=round(vs0_m_s, 4),
                output_unit_si="m/s",
                secondary_display_value=round(vs0_knots, 3),
                secondary_display_unit="knots",
                source_citation_id="FAA-14CFR-23-2110",
            )
        )

    # Reynolds number
    reynolds_number: Optional[float] = None
    if true_airspeed_m_s is not None and wingspan_m is not None and wing_area_m2 is not None:
        mean_chord = wing_area_m2 / wingspan_m
        reynolds_number = (density * true_airspeed_m_s * mean_chord) / dynamic_viscosity

    # Static margin
    static_margin: Optional[float] = None
    if (
        state.center_of_gravity_position is not None
        and state.neutral_point_position is not None
        and state.mean_aerodynamic_chord is not None
    ):
        xcg_m, _ = convert_quantity_to_si("cg", state.center_of_gravity_position, "meter")
        xnp_m, _ = convert_quantity_to_si("np", state.neutral_point_position, "meter")
        mac_m, _ = convert_quantity_to_si("mac", state.mean_aerodynamic_chord, "meter")
        if mac_m <= 0:
            raise AerodynamicDomainError("Mean aerodynamic chord must be strictly positive.")
        static_margin = (xnp_m - xcg_m) / mac_m

    # Climb gradient
    climb_gradient_pct: Optional[float] = None
    if state.available_thrust is not None and d_total_newtons is not None and weight_n is not None:
        t_avail_n, _ = convert_quantity_to_si("thrust", state.available_thrust, "newton")
        sin_gamma = (t_avail_n - d_total_newtons) / weight_n
        clamped_sin_gamma = max(-1.0, min(1.0, sin_gamma))
        climb_gradient_pct = 100.0 * math.tan(math.asin(clamped_sin_gamma))

    # Breguet Range
    breguet_range_km: Optional[float] = None
    if (
        state.propeller_efficiency is not None
        and state.specific_fuel_consumption is not None
        and state.fuel_mass is not None
        and mass_kg is not None
        and ld_ratio is not None
    ):
        fuel_m_kg, _ = convert_quantity_to_si("fuel_mass", state.fuel_mass, "kilogram")
        sfc_val = state.specific_fuel_consumption.numerical_value
        if fuel_m_kg < mass_kg and sfc_val > 0:
            w_initial = mass_kg * STANDARD_GRAVITY_M_S2
            w_final = (mass_kg - fuel_m_kg) * STANDARD_GRAVITY_M_S2
            range_meters = (state.propeller_efficiency / sfc_val) * ld_ratio * math.log(w_initial / w_final)
            breguet_range_km = range_meters / 1000.0

    bundle = PhysicsSolutionBundle(
        altitude_meters=altitude_m,
        air_density_kg_m3=round(density, 6),
        static_pressure_pascals=round(pressure, 2),
        temperature_kelvin=round(temperature, 2),
        speed_of_sound_m_s=round(speed_of_sound, 3),
        dynamic_pressure_pascals=round(dynamic_pressure_pa, 4) if dynamic_pressure_pa is not None else None,
        aspect_ratio=round(aspect_ratio, 6) if aspect_ratio is not None else None,
        wing_loading_n_m2=round(wing_loading_n_m2, 4) if wing_loading_n_m2 is not None else None,
        wing_loading_kg_m2=round(wing_loading_kg_m2, 4) if wing_loading_kg_m2 is not None else None,
        lift_coefficient_cl=round(cl, 6) if cl is not None else None,
        induced_drag_coefficient_cdi=round(cdi, 6) if cdi is not None else None,
        induced_drag_force_newtons=round(di_newtons, 4) if di_newtons is not None else None,
        total_drag_coefficient_cd=round(cd, 6) if cd is not None else None,
        total_drag_force_newtons=round(d_total_newtons, 4) if d_total_newtons is not None else None,
        lift_to_drag_ratio=round(ld_ratio, 4) if ld_ratio is not None else None,
        stall_speed_vs0_m_s=round(vs0_m_s, 4) if vs0_m_s is not None else None,
        stall_speed_vs0_knots=round(vs0_knots, 3) if vs0_knots is not None else None,
        mach_number=round(mach, 4) if mach is not None else None,
        reynolds_number=round(reynolds_number, 1) if reynolds_number is not None else None,
        prandtl_glauert_beta=round(prandtl_beta, 4) if prandtl_beta is not None else None,
        prandtl_glauert_cp_corrected=round(prandtl_glauert_cp, 4) if prandtl_glauert_cp is not None else None,
        critical_mach_number=round(m_cr, 4) if m_cr is not None else None,
        drag_divergence_mach_number=round(m_dd, 4) if m_dd is not None else None,
        wave_drag_coefficient_cdw=round(cdw, 6) if cdw is not None else None,
        wave_drag_force_newtons=round(dw_newtons, 4) if dw_newtons is not None else None,
        static_margin_fraction=round(static_margin, 4) if static_margin is not None else None,
        climb_gradient_percent=round(climb_gradient_pct, 2) if climb_gradient_pct is not None else None,
        breguet_range_kilometers=round(breguet_range_km, 2) if breguet_range_km is not None else None,
        equation_traces=equation_traces,
    )

    return bundle, unit_conversions

