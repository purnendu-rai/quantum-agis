"""Performance tests: the verification pipeline must stay under 100 ms per run.

Measures the full 6-layer stack (including Monte Carlo and quantum-walk
components) across 1000 sequential runs and asserts both mean and tail
latency budgets.
"""

from __future__ import annotations

import statistics
import time

import pytest

from app.engine.verification_engine import get_engine

#: Number of timed verification runs.
NUM_RUNS: int = 1000
#: Mean latency budget per verification (ms).
MEAN_BUDGET_MS: float = 100.0
#: Tail latency budget (p99 must stay well clear of the mean budget).
P99_BUDGET_MS: float = 250.0


@pytest.mark.asyncio
async def test_verification_latency_under_100ms_for_1000_runs():
    """1000 verifications average < 100 ms each with a bounded tail."""
    engine = get_engine()

    # Warm-up: first call pays import/compilation costs (qutip-less paths are
    # pure numpy, but the first hit still allocates caches).
    await engine.verify({"signature": "AGIS-warmup", "session_id": "perf"})

    durations_ms: list[float] = []
    for index in range(NUM_RUNS):
        started = time.perf_counter()
        result = await engine.verify(
            {"signature": f"AGIS-perf-{index:05d}", "session_id": "perf"}
        )
        durations_ms.append((time.perf_counter() - started) * 1000.0)
        assert result["decision"] in ("ACCEPT", "QUARANTINE", "REJECT")

    mean_ms = statistics.mean(durations_ms)
    p99_ms = sorted(durations_ms)[int(0.99 * len(durations_ms)) - 1]
    max_ms = max(durations_ms)

    print(
        f"\nverification latency over {NUM_RUNS} runs: "
        f"mean={mean_ms:.2f}ms median={statistics.median(durations_ms):.2f}ms "
        f"p99={p99_ms:.2f}ms max={max_ms:.2f}ms"
    )
    assert mean_ms < MEAN_BUDGET_MS, f"mean latency {mean_ms:.2f}ms exceeds {MEAN_BUDGET_MS}ms"
    assert p99_ms < P99_BUDGET_MS, f"p99 latency {p99_ms:.2f}ms exceeds {P99_BUDGET_MS}ms"
