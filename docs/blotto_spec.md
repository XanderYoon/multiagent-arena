# Blotto Specification

## Variant Definition

The repository now treats Blotto as the following default variant:

- Variant id: `discrete_blotto_v1`
- Action space: discrete integer troop allocations
- Battlefield count: configurable
- Troop budget: configurable
- Payoff policy:
  - `random_range`: each battlefield value is sampled independently from a configured integer range
  - `fixed`: the full battlefield value vector is supplied directly

This matches the current prototype benchmark while making the parameters explicit and configurable.

## Allocation Validation

A Blotto allocation is valid only if all of the following hold:

- It is a list
- Its length equals the configured battlefield count
- Every entry is an integer
- Every entry is non-negative
- The entries sum exactly to the configured troop budget

## Baseline Opponents

The environment now supports these baseline bot policies:

- `uniform`: spreads troops as evenly as possible
- `random`: samples a feasible discrete allocation
- `high_value_targeting`: allocates proportionally to squared battlefield values to over-weight high-value battlefields
- `nash_approx`: allocates proportionally to battlefield values as a principled equilibrium approximation

## Nash Distance Approximation

Exact Nash distance for general Blotto variants is not implemented. The repository now uses a principled approximation:

- Compute an equilibrium proxy by allocating troops proportionally to battlefield values
- Measure distance from a candidate allocation to that proxy with L1 distance
- Report both raw and normalized L1 distance

This is stored in Blotto match outputs as `nash_distance`.

## Consistency Definition

For Blotto, consistency should be measured across repeated trials using:

- Allocation variance: average pairwise L1 distance between allocations for matched states
- Outcome stability: whether the same architecture wins under repeated matched-seed runs
- Equilibrium stability: variance in normalized Nash-distance across repeated trials

The current implementation defines this policy and exposes the per-trial ingredients needed for later aggregation.
