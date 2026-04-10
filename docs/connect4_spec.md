# Connect 4 Specification

## Variant Decision

The repository currently uses standard Connect 4 as the default evaluated variant:

- Variant id: `gravity_grid_standard_v1`
- Default board size: `7 x 6`
- Default connect length: `4`

The implementation is configurable, so non-standard board sizes and connect lengths are supported by the engine and config even though the current benchmark default remains standard.

## Prompt Wording

The benchmark refers to the game as a "gravity-grid game" in prompts. The prompt/state contract assumes:

- Columns are `0`-indexed
- Rows are rendered top to bottom
- A move is a single integer column choice
- The token falls to the lowest empty slot in the chosen column

The environment state description explicitly includes this orientation note to avoid mismatch between the rendered board and the legal move semantics.

## Oracle Strength

The current oracle is a depth-limited minimax search with:

- Alpha-beta pruning
- A heuristic evaluation function for non-terminal leaf states
- Explicit handling of immediate wins and losses through terminal scoring

This is stronger than the prior constant-value leaf evaluation, but it is still not a perfect solver at arbitrary depth. The limitation should be acknowledged in analysis.

## Optimal Move Accuracy Metric

The repository now defines Connect 4 oracle accuracy as:

- Primary criterion: the agent matches any oracle-equivalent best move
- Secondary criterion: the oracle value gap between the chosen move and the best oracle value

Per evaluated state, the benchmark records:

- `best_moves`
- `best_score`
- `move_scores`
- `chosen_move`
- `chosen_move_score`
- `matched_any_optimal_move`
- `value_gap`

This avoids over-penalizing the agent when multiple moves are equally optimal.
