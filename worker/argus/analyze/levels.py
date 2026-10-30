"""The next levels of a numeric factor (D-80): Ax (Meta's Bayesian optimization, KB 11) proposes them from each finished
vessel's level and judged outcome. Ax picks the numbers; the model only explains them. Imported lazily: Ax brings
PyTorch, and only a suggestion for a numeric factor needs it."""

from __future__ import annotations

import logging
import math
import warnings
from collections.abc import Sequence

PARAMETER = "level"
OUTCOME = "outcome"


def level_bounds(levels: Sequence[float]) -> tuple[float, float]:
    """The tested range widened by half its width on each side, never below 0. One level gets half its size around
    it (at least 1), so there is still a range to search."""
    low, high = min(levels), max(levels)
    half = (high - low) / 2 if high > low else max(abs(low) / 2, 1.0)
    return max(0.0, low - half), high + half


def _rounded(value: float, bounds: tuple[float, float]) -> float:
    """To a hundredth of the search range's order of magnitude: 33.2817 in (10, 50) becomes 33.3."""
    width = bounds[1] - bounds[0]
    places = max(0, 2 - math.floor(math.log10(width))) if width > 0 else 2
    return min(max(round(value, places), bounds[0]), bounds[1])  # rounding never takes a pick outside the range


def suggest_levels(
    tested: Sequence[tuple[float, float]],
    *,
    minimize: bool,
    bounds: tuple[float, float],
    count: int = 3,
    seed: int = 0,
) -> list[float]:
    """`count` levels to try next, lowest first (see level_picks)."""
    return sorted(level for level, _ in level_picks(tested, minimize=minimize, bounds=bounds, count=count, seed=seed))


def level_picks(
    tested: Sequence[tuple[float, float]],
    *,
    minimize: bool,
    bounds: tuple[float, float],
    count: int = 3,
    seed: int = 0,
) -> list[tuple[float, str]]:
    """`count` levels to try next, each with the Ax generation node that picked it ("MBM": its BoTorch model), from
    (level, outcome) per finished vessel: one range parameter, each pair attached and completed as a trial. Ax's usual
    quasi-random start is switched off, since the attached vessels already cover the range: every pick comes from the
    model of this run's data, on a small plate too."""
    with warnings.catch_warnings():  # Ax and PyTorch warn about their own deprecations on import and while fitting
        warnings.simplefilter("ignore")
        from ax.api.client import Client
        from ax.api.configs import RangeParameterConfig

        for name in [n for n in logging.root.manager.loggerDict if n.split(".")[0] == "ax"]:
            logging.getLogger(name).setLevel(logging.ERROR)  # each Ax module logs every trial at INFO
        client = Client(random_seed=seed)
        client.configure_experiment(
            name="argus_next_levels",
            parameters=[RangeParameterConfig(name=PARAMETER, bounds=bounds, parameter_type="float")],
        )
        client.configure_optimization(objective=f"-{OUTCOME}" if minimize else OUTCOME)
        client.configure_generation_strategy(initialization_budget=0, initialize_with_center=False)
        for level, outcome in tested:
            index = client.attach_trial(parameters={PARAMETER: float(level)})
            client.complete_trial(trial_index=index, raw_data={OUTCOME: float(outcome)})
        trials = client.get_next_trials(max_trials=count)
        nodes = client.summarize().set_index("trial_index")["generation_node"]
    return [(_rounded(float(p[PARAMETER]), bounds), str(nodes[index])) for index, p in trials.items()]
