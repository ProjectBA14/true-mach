"""Pydantic data schemas for AeroGuard-RAG state, gatekeeping, and physics traces."""

from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
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
    "transonic_audit",
    "wing_sizing",
    "regulatory_qa",
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
    altitude_meters: float = 0.0
    air_density_kg_m3: float = 1.225
    static_pressure_pascals: float = 101325.0
    temperature_kelvin: float = 288.15
    speed_of_sound_m_s: float = 340.294
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
    prandtl_glauert_beta: Optional[float] = None
    prandtl_glauert_cp_corrected: Optional[float] = None
    critical_mach_number: Optional[float] = None
    drag_divergence_mach_number: Optional[float] = None
    wave_drag_coefficient_cdw: Optional[float] = None
    wave_drag_force_newtons: Optional[float] = None
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
    airfoil_thickness_ratio: Optional[float] = None
    wing_sweep_degrees: Optional[float] = None
    airfoil_technology_factor: Optional[float] = None

    # Relay Artifacts
    missing_parameters: List[str] = Field(default_factory=list)
    regulatory_category: Optional[str] = None
    certification_level: Optional[str] = None
    unit_conversions: List[UnitConversionRecord] = Field(default_factory=list)
    retrieved_citations: List[RegulatoryCitation] = Field(default_factory=list)
    latest_physics_solution: Optional[PhysicsSolutionBundle] = None
    latest_compliance_report: Optional[ComplianceReport] = None
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)


class ExtractedTurnParameters(BaseModel):
    """Parameters extracted from a single user turn."""
    calculation_intent: Optional[CalculationIntentType] = None
    wingspan: Optional[DimensionalQuantityInput] = None
    wing_area: Optional[DimensionalQuantityInput] = None
    aircraft_mass: Optional[DimensionalQuantityInput] = None
    passenger_count: Optional[int] = None
    true_airspeed: Optional[DimensionalQuantityInput] = None
    altitude: Optional[DimensionalQuantityInput] = None
    oswald_efficiency_factor: Optional[float] = None
    zero_lift_drag_coefficient_cd0: Optional[float] = None
    maximum_lift_coefficient_clmax: Optional[float] = None
    available_thrust: Optional[DimensionalQuantityInput] = None
    center_of_gravity_position: Optional[DimensionalQuantityInput] = None
    neutral_point_position: Optional[DimensionalQuantityInput] = None
    mean_aerodynamic_chord: Optional[DimensionalQuantityInput] = None
    fuel_mass: Optional[DimensionalQuantityInput] = None
    propeller_efficiency: Optional[float] = None
    specific_fuel_consumption: Optional[DimensionalQuantityInput] = None
    incompressible_pressure_coefficient_cp0: Optional[float] = None
    airfoil_thickness_ratio: Optional[float] = None
    wing_sweep_degrees: Optional[float] = None
    airfoil_technology_factor: Optional[float] = None
    confirmed_standard_isa_defaults: bool = False

