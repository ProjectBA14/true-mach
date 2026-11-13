# Physics Solver Rules

1. **Zero LLM Math Protocol:**
   - The LLM is strictly prohibited from computing, estimating, or rounding any aerodynamic numbers or conversion factors.
   - All floating-point arithmetic and unit conversions MUST execute deterministically in Python using `AeroSandbox`, `SymPy`, and `pint`.

2. **Dimensional Analysis & SI Base Units:**
   - All raw user inputs must be converted to strict SI base units (`meters`, `meters**2`, `kilograms`, `meters/second`, `kelvin`, `pascal`, `newtons`) before passing into aerodynamic equations.
   - If a user passes weight/force (`lbf` or `N`) for mass, convert via $m = W / g_0$ with $g_0 = 9.80665\text{ m/s}^2$.
   - Any dimensionality mismatch must raise a typed `pint.DimensionalityError` immediately (Fail Fast).

3. **Symbolic Trace Integrity:**
   - Every calculation must generate a corresponding `EquationTrace` with canonical symbolic LaTeX and numerical substitution LaTeX.
   - Numerical evaluation in double precision (`float64`) must match SymPy substitution within $10^{-9}$ relative tolerance.

4. **Atmosphere Model:**
   - ISA atmosphere must be evaluated using `aerosandbox.Atmosphere(altitude=altitude_meters)` on CPU.

5. **Parameter Sweep SI Consistency:**
   - Parameter sweep and design advisory routines (`run_parameter_sweep_advisor` in `compliance.py`) must ALWAYS operate on Pint SI-normalized values (`state.unit_conversions` or `aero_solver.py` SI conversions) rather than raw user unit values to guarantee valid optimization trajectories regardless of input unit systems (Imperial, Aviation, or SI).


