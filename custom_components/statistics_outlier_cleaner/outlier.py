"""Outlier detection for Home Assistant long-term statistics.

Replicates the algorithm used by the Developer Tools > Statistics > Outliers
feature, plus threshold-based and MAD-based methods safer for scheduled use.

Reference: home-assistant/frontend
  src/panels/config/developer-tools/statistics/dialog-statistics-adjust-sum.ts

Key facts mirrored from the upstream implementation:
  * Outliers operate on the per-period ``change`` field, NOT on ``state`` or ``sum``.
  * For "hour" period: every record's ``change`` is examined.
  * For "5minute" period: the FIRST datapoint is dropped (upstream convention —
    it contains the entire historical sum as its change).
  * In the "hybrid" mode (what the dev-tools dialog does): fetch BOTH hour and
    5minute data; for each hour, if all 12 five-minute samples exist use them,
    otherwise fall back to the hourly value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Iterable, Literal

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    list_statistic_ids,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

Period = Literal["hour", "5minute", "hybrid"]
Method = Literal["top_n", "absolute", "mad"]


@dataclass
class OutlierCandidate:
    """A single statistics row flagged as an outlier."""

    start: int  # ms epoch
    end: int    # ms epoch
    change: float
    state: float | None
    period: str  # "hour" or "5minute"

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "change": self.change,
            "state": self.state,
            "period": self.period,
        }


@dataclass
class OutlierReport:
    """Result of an outlier scan."""

    statistic_id: str
    method: Method
    period_requested: Period
    candidates: list[OutlierCandidate] = field(default_factory=list)
    median: float | None = None
    mad: float | None = None
    scanned_rows: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "statistic_id": self.statistic_id,
            "method": self.method,
            "period_requested": self.period_requested,
            "candidates": [c.to_dict() for c in self.candidates],
            "median": self.median,
            "mad": self.mad,
            "scanned_rows": self.scanned_rows,
        }


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


async def get_sum_statistic_ids(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Return statistic IDs that have a sum (total / total_increasing)."""
    recorder = get_instance(hass)
    all_ids = await recorder.async_add_executor_job(list_statistic_ids, hass)
    return [s for s in all_ids if s.get("has_sum")]


async def is_sum_statistic(hass: HomeAssistant, statistic_id: str) -> bool:
    """Check that a given statistic_id supports sum adjustment."""
    sums = await get_sum_statistic_ids(hass)
    return any(s["statistic_id"] == statistic_id for s in sums)


# ---------------------------------------------------------------------------
# Data fetch (read-only; uses the recorder's public Python API)
# ---------------------------------------------------------------------------


async def _fetch_period(
    hass: HomeAssistant,
    statistic_id: str,
    period: Literal["hour", "5minute"],
    lookback_days: int,
) -> list[dict[str, Any]]:
    """Fetch raw statistics rows for one period via the recorder API."""
    recorder = get_instance(hass)
    if lookback_days > 0:
        start_time = dt_util.utcnow() - timedelta(days=lookback_days)
    else:
        start_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
    end_time = dt_util.utcnow()

    raw = await recorder.async_add_executor_job(
        statistics_during_period,
        hass,
        start_time,
        end_time,
        {statistic_id},
        period,
        None,
        {"change", "state"},
    )
    return raw.get(statistic_id, []) or []


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


def _to_ms_epoch(value: Any) -> int:
    """Normalise a start/end field to a millisecond epoch int."""
    if isinstance(value, (int, float)):
        return int(value * 1000) if value < 1e12 else int(value)
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    raise TypeError(f"Unexpected start/end type: {type(value)!r}")


def _normalise_rows(
    rows: Iterable[dict[str, Any]], period_label: str
) -> list[OutlierCandidate]:
    """Convert raw recorder rows to OutlierCandidate, dropping rows with no change."""
    out: list[OutlierCandidate] = []
    for r in rows:
        change = r.get("change")
        if change is None:
            continue
        out.append(
            OutlierCandidate(
                start=_to_ms_epoch(r["start"]),
                end=_to_ms_epoch(r["end"]),
                change=float(change),
                state=float(r["state"]) if r.get("state") is not None else None,
                period=period_label,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Detection algorithms
# ---------------------------------------------------------------------------


def _algo_top_n(
    candidates: list[OutlierCandidate], top_n: int
) -> list[OutlierCandidate]:
    """Top N by |change|, descending — matches the dev-tools JS exactly.

    Not safe for unattended scheduled runs: it always returns something.
    """
    return sorted(candidates, key=lambda c: abs(c.change), reverse=True)[:top_n]


def _algo_absolute(
    candidates: list[OutlierCandidate], threshold: float
) -> list[OutlierCandidate]:
    """Flag any row whose |change| >= threshold."""
    return [c for c in candidates if abs(c.change) >= threshold]


def _algo_mad(
    candidates: list[OutlierCandidate], mad_factor: float
) -> tuple[list[OutlierCandidate], float, float]:
    """Median Absolute Deviation method.

    Modified z-score = 0.6745 * (x - median) / MAD.
    Returns (flagged, median, mad).

    When MAD is zero (flat sensor), returns an empty list rather than
    flagging everything — conservative behaviour for unattended use.
    """
    if not candidates:
        return [], 0.0, 0.0

    # Compute MAD on non-zero changes only.  Sensors that reset daily (e.g.
    # pv_energy_today_kwh) have many zero-change rows at night; including them
    # drives the median to 0 and collapses MAD to 0, hiding real spikes.
    nonzero = [c for c in candidates if c.change != 0]
    stat_candidates = nonzero if nonzero else candidates
    values = [c.change for c in stat_candidates]
    values_sorted = sorted(values)
    median = _median_sorted(values_sorted)
    deviations = sorted(abs(v - median) for v in values)
    mad = _median_sorted(deviations)

    if mad == 0:
        _LOGGER.debug("MAD is zero — sensor appears flat. Skipping MAD detection.")
        return [], median, 0.0

    flagged: list[OutlierCandidate] = []
    for c in candidates:
        modified_z = 0.6745 * (c.change - median) / mad
        if abs(modified_z) >= mad_factor:
            flagged.append(c)
    return flagged, median, mad


def _median_sorted(sorted_values: list[float]) -> float:
    n = len(sorted_values)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2 == 1:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0


# ---------------------------------------------------------------------------
# Hybrid period reconciliation (mirrors the dev-tools dialog)
# ---------------------------------------------------------------------------


def _hybrid_rows(
    hour_rows: list[OutlierCandidate],
    five_min_rows: list[OutlierCandidate],
) -> list[OutlierCandidate]:
    """Reconcile hour + 5-minute rows the way the frontend does.

    For each hour: if it has exactly 12 five-minute samples, use them.
    Otherwise (partial hour) use the hourly value.

    The FIRST five-minute sample is always dropped — it contains the entire
    historical sum as its change (per upstream comment in the frontend code).
    """
    if five_min_rows:
        five_min_rows = five_min_rows[1:]

    by_hour: dict[int, list[OutlierCandidate]] = {h.start: [] for h in hour_rows}
    hour_lookup = {h.start: h for h in hour_rows}
    hour_keys_sorted = sorted(by_hour.keys())

    i = 0
    leftover: list[OutlierCandidate] = []
    for s in sorted(five_min_rows, key=lambda x: x.start):
        matched = False
        while i < len(hour_keys_sorted):
            hour_start = hour_keys_sorted[i]
            hour = hour_lookup[hour_start]
            if s.start >= hour.start and s.end <= hour.end:
                by_hour[hour_start].append(s)
                matched = True
                break
            if s.start >= hour.end:
                i += 1
                continue
            break
        if not matched:
            leftover.append(s)

    result: list[OutlierCandidate] = []
    for hour in hour_rows:
        children = by_hour[hour.start]
        if len(children) == 12:
            result.extend(children)
        else:
            result.append(hour)
    result.extend(leftover)
    return result


# ---------------------------------------------------------------------------
# Top-level scan (read-only)
# ---------------------------------------------------------------------------


async def scan_outliers(
    hass: HomeAssistant,
    statistic_id: str,
    *,
    period: Period = "hybrid",
    method: Method = "top_n",
    top_n: int = 10,
    threshold: float = 0.0,
    mad_factor: float = 6.0,
    lookback_days: int = 0,
) -> OutlierReport:
    """Run an outlier scan and return a report. No mutation."""
    if period == "hour":
        raw = await _fetch_period(hass, statistic_id, "hour", lookback_days)
        candidates = _normalise_rows(raw, "hour")
    elif period == "5minute":
        raw = await _fetch_period(hass, statistic_id, "5minute", lookback_days)
        rows = _normalise_rows(raw, "5minute")
        candidates = rows[1:] if rows else []
    else:  # hybrid
        hour_raw = await _fetch_period(hass, statistic_id, "hour", lookback_days)
        five_raw = await _fetch_period(hass, statistic_id, "5minute", lookback_days)
        candidates = _hybrid_rows(
            _normalise_rows(hour_raw, "hour"),
            _normalise_rows(five_raw, "5minute"),
        )

    scanned = len(candidates)
    median: float | None = None
    mad: float | None = None

    if method == "top_n":
        flagged = _algo_top_n(candidates, top_n)
    elif method == "absolute":
        if threshold <= 0:
            raise ValueError("absolute method requires a positive 'threshold' parameter")
        flagged = _algo_absolute(candidates, threshold)
    elif method == "mad":
        flagged, median, mad = _algo_mad(candidates, mad_factor)
    else:
        raise ValueError(f"Unknown method: {method!r}")

    flagged = sorted(flagged, key=lambda c: abs(c.change), reverse=True)

    return OutlierReport(
        statistic_id=statistic_id,
        method=method,
        period_requested=period,
        candidates=flagged,
        median=median,
        mad=mad,
        scanned_rows=scanned,
    )
