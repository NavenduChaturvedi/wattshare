from typing import Literal, Optional

GridHealth = Literal["green", "yellow", "red"]

# Transformer utilisation bands (% of rated capacity), in either flow direction:
# heavy evening import and heavy midday solar export (reverse flow) both stress it.
MODERATE_LOAD_PCT = 50.0
HIGH_LOAD_PCT = 80.0


def compute_grid_health(transformer_load_pct: Optional[float]) -> GridHealth:
    """Green: comfortable headroom. Yellow: working hard. Red: near or over rated capacity.
    No reading yet (no cycle has run) is reported as green."""
    if transformer_load_pct is None or transformer_load_pct < MODERATE_LOAD_PCT:
        return "green"
    if transformer_load_pct < HIGH_LOAD_PCT:
        return "yellow"
    return "red"
