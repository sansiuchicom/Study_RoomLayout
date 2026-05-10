"""Domain feasibility gates as pure functions (Step 06, S06-D13).

Each gate is `(inputs) -> None` and raises a subclass of
`proto3.schema.validation.DomainGateFailure` on infeasibility.

Population order (Plan §4):
- §4.4 lands `check_min_area`, `check_min_dim`, `check_access_schema`,
  `check_multi_floor_feasibility` together with the failure hierarchy.
- §4.6 wires Stage 02 to call them.
- Stage 11/13 binding deferred to Step 12 (Plan Def-5).

This module is currently a scaffold; concrete signatures and bodies
arrive in §4.4.
"""
