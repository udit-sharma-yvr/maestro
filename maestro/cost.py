"""Per-model token pricing and a running cost tracker.

Prices are USD per 1,000,000 tokens. Override the table in production (or read from a
config) — these are approximate public list prices and the whole point is to make the
cost-aware routing visible and measurable.
"""

from dataclasses import dataclass


# Per 1M tokens (USD).
PRICING = {
    "claude-3-5-haiku-20241022": {"in": 0.80, "out": 4.00},
    "claude-3-5-sonnet-20241022": {"in": 3.00, "out": 15.00},
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4o": {"in": 2.50, "out": 10.00},
}


@dataclass
class CostBreakdown:
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float

    @property
    def total_cost(self) -> float:
        return self.input_cost + self.output_cost


class CostTracker:
    """Accumulates token usage and cost across a single task run."""

    def __init__(self) -> None:
        self.total_in = 0
        self.total_out = 0
        self.total_cost = 0.0
        self.by_model: dict[str, dict] = {}

    def add(self, model: str, usage: dict) -> CostBreakdown:
        in_t = usage.get("input_tokens", 0)
        out_t = usage.get("output_tokens", 0)
        price = PRICING.get(model, {"in": 0.0, "out": 0.0})
        in_cost = in_t / 1_000_000 * price["in"]
        out_cost = out_t / 1_000_000 * price["out"]
        bd = CostBreakdown(model, in_t, out_t, in_cost, out_cost)

        self.total_in += in_t
        self.total_out += out_t
        self.total_cost += bd.total_cost

        m = self.by_model.setdefault(model, {"in": 0, "out": 0, "cost": 0.0})
        m["in"] += in_t
        m["out"] += out_t
        m["cost"] += bd.total_cost
        return bd

    def snapshot(self) -> dict:
        return {
            "input_tokens": self.total_in,
            "output_tokens": self.total_out,
            "total_cost": round(self.total_cost, 6),
            "by_model": {
                k: {**v, "cost": round(v["cost"], 6)} for k, v in self.by_model.items()
            },
        }
