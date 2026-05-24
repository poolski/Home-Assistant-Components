"""Unit tests for pure outlier-detection algorithm functions.

No Home Assistant stack required — the HA imports are stubbed in conftest.py.
"""

from __future__ import annotations

import math
import sys

import pytest

# conftest.py stubs HA modules; add the project root so the component is importable.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from custom_components.statistics_outlier_cleaner.outlier import (
    OutlierCandidate,
    _algo_absolute,
    _algo_mad,
    _algo_top_n,
    _hybrid_rows,
    _median_sorted,
    _normalise_rows,
    _to_ms_epoch,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _candidate(start_ms: int, change: float, state: float = 0.0, period: str = "hour") -> OutlierCandidate:
    return OutlierCandidate(
        start=start_ms,
        end=start_ms + 3_600_000,
        change=change,
        state=state,
        period=period,
    )


def _hour(start_ms: int, change: float, state: float = 0.0) -> OutlierCandidate:
    return _candidate(start_ms, change, state, period="hour")


def _five_min(start_ms: int, change: float, state: float = 0.0) -> OutlierCandidate:
    return OutlierCandidate(
        start=start_ms,
        end=start_ms + 300_000,
        change=change,
        state=state,
        period="5minute",
    )


# ---------------------------------------------------------------------------
# _to_ms_epoch
# ---------------------------------------------------------------------------


class TestToMsEpoch:
    def test_converts_seconds_float_to_ms(self):
        assert _to_ms_epoch(1_000_000.0) == 1_000_000_000

    def test_already_ms_passes_through(self):
        # Any value >= 1e12 is treated as already in ms
        assert _to_ms_epoch(1_700_000_000_000) == 1_700_000_000_000

    def test_integer_seconds(self):
        assert _to_ms_epoch(1000) == 1_000_000

    def test_datetime_object(self):
        from datetime import datetime, timezone

        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        expected = int(dt.timestamp() * 1000)
        assert _to_ms_epoch(dt) == expected

    def test_unsupported_type_raises(self):
        import pytest

        with pytest.raises(TypeError):
            _to_ms_epoch("not-a-timestamp")


# ---------------------------------------------------------------------------
# _normalise_rows
# ---------------------------------------------------------------------------


class TestNormaliseRows:
    def test_drops_rows_with_none_change(self):
        rows = [
            {"start": 0, "end": 1000, "change": None, "state": 1.0},
            {"start": 1000, "end": 2000, "change": 5.0, "state": 2.0},
        ]
        result = _normalise_rows(rows, "hour")
        assert len(result) == 1
        assert result[0].change == 5.0

    def test_keeps_zero_change(self):
        rows = [{"start": 0, "end": 1000, "change": 0.0, "state": 1.0}]
        result = _normalise_rows(rows, "hour")
        assert len(result) == 1
        assert result[0].change == 0.0

    def test_converts_seconds_to_ms(self):
        rows = [{"start": 1000.0, "end": 4600.0, "change": 1.0, "state": None}]
        result = _normalise_rows(rows, "hour")
        assert result[0].start == 1_000_000
        assert result[0].end == 4_600_000

    def test_state_none_stored_as_none(self):
        rows = [{"start": 0, "end": 1000, "change": 1.0, "state": None}]
        result = _normalise_rows(rows, "hour")
        assert result[0].state is None

    def test_period_label_applied(self):
        rows = [{"start": 0, "end": 1000, "change": 1.0, "state": 0.0}]
        assert _normalise_rows(rows, "5minute")[0].period == "5minute"


# ---------------------------------------------------------------------------
# _median_sorted
# ---------------------------------------------------------------------------


class TestMedianSorted:
    def test_empty_list(self):
        assert _median_sorted([]) == 0.0

    def test_single_element(self):
        assert _median_sorted([7.0]) == 7.0

    def test_odd_count(self):
        assert _median_sorted([1.0, 3.0, 5.0]) == 3.0

    def test_even_count(self):
        assert _median_sorted([1.0, 3.0]) == 2.0

    def test_larger_list(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        assert _median_sorted(values) == 3.5


# ---------------------------------------------------------------------------
# _algo_top_n
# ---------------------------------------------------------------------------


class TestAlgoTopN:
    def test_returns_top_n_by_abs_change(self):
        candidates = [_hour(i * 1000, float(i)) for i in range(10)]
        result = _algo_top_n(candidates, 3)
        assert len(result) == 3
        assert [c.change for c in result] == [9.0, 8.0, 7.0]

    def test_negative_change_ranked_by_abs(self):
        candidates = [_hour(0, 10.0), _hour(1000, -50.0), _hour(2000, 5.0)]
        result = _algo_top_n(candidates, 1)
        assert result[0].change == -50.0

    def test_returns_all_when_fewer_than_n(self):
        candidates = [_hour(0, 1.0), _hour(1000, 2.0)]
        result = _algo_top_n(candidates, 10)
        assert len(result) == 2

    def test_empty_input(self):
        assert _algo_top_n([], 5) == []

    def test_n_equals_one(self):
        candidates = [_hour(0, 3.0), _hour(1000, 100.0), _hour(2000, 2.0)]
        result = _algo_top_n(candidates, 1)
        assert len(result) == 1
        assert result[0].change == 100.0

    def test_stable_sort_preserves_large_n_ordering(self):
        candidates = [_hour(i * 1000, float(10 - i)) for i in range(10)]
        result = _algo_top_n(candidates, 10)
        changes = [c.change for c in result]
        assert changes == sorted(changes, reverse=True)


# ---------------------------------------------------------------------------
# _algo_absolute
# ---------------------------------------------------------------------------


class TestAlgoAbsolute:
    def test_flags_rows_above_threshold(self):
        candidates = [_hour(0, 5.0), _hour(1000, 200.0), _hour(2000, 3.0)]
        result = _algo_absolute(candidates, threshold=100.0)
        assert len(result) == 1
        assert result[0].change == 200.0

    def test_does_not_flag_at_threshold(self):
        # Docs say |change| >= threshold; equality should be flagged.
        candidates = [_hour(0, 100.0)]
        result = _algo_absolute(candidates, threshold=100.0)
        assert len(result) == 1

    def test_negative_change_evaluated_by_abs(self):
        candidates = [_hour(0, -500.0), _hour(1000, 50.0)]
        result = _algo_absolute(candidates, threshold=200.0)
        assert len(result) == 1
        assert result[0].change == -500.0

    def test_returns_empty_when_nothing_exceeds(self):
        candidates = [_hour(i * 1000, float(i)) for i in range(5)]
        result = _algo_absolute(candidates, threshold=1000.0)
        assert result == []

    def test_empty_input(self):
        assert _algo_absolute([], threshold=1.0) == []


# ---------------------------------------------------------------------------
# _algo_mad
# ---------------------------------------------------------------------------


class TestAlgoMad:
    def _make_varying_with_spike(self, spike_change: float = 1_000_000.0) -> list[OutlierCandidate]:
        """Varying data (0.5–1.5 kWh/h) with a single huge spike.

        Using genuinely varying (not flat) normal values ensures MAD > 0 so
        the algorithm has a baseline to compare against.  Pure-flat data
        (all identical) yields MAD = 0 and correctly returns [] per the spec.
        """
        normal_changes = [0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 0.8, 1.2, 0.6, 1.4]
        normal = [_hour(i * 3_600_000, c) for i, c in enumerate(normal_changes)]
        spike = _hour(200 * 3_600_000, spike_change)
        return normal + [spike]

    def test_flags_obvious_spike(self):
        candidates = self._make_varying_with_spike(1_000_000.0)
        flagged, _, _ = _algo_mad(candidates, mad_factor=6.0)
        assert len(flagged) == 1
        assert flagged[0].change == 1_000_000.0

    def test_does_not_flag_clean_data(self):
        # Slightly varying data; nothing extreme.
        changes = [1.0, 1.1, 0.9, 1.05, 0.95, 1.02, 0.98, 1.0, 1.03, 0.97]
        candidates = [_hour(i * 3_600_000, c) for i, c in enumerate(changes)]
        flagged, _, _ = _algo_mad(candidates, mad_factor=6.0)
        assert flagged == []

    def test_returns_median_and_mad(self):
        # Use varying normal values so MAD > 0 (pure-flat data gives MAD=0).
        values = [1.0, 1.1, 0.9, 1.05, 0.95, 1_000_000.0]
        candidates = [_hour(i * 3_600_000, v) for i, v in enumerate(values)]
        flagged, median, mad = _algo_mad(candidates, mad_factor=3.0)
        assert median == pytest.approx(1.025)
        assert mad > 0.0
        assert len(flagged) == 1

    def test_mad_zero_edge_case_returns_empty(self):
        # All identical values → MAD = 0. Must return [] not everything.
        candidates = [_hour(i * 3_600_000, 5.0) for i in range(20)]
        flagged, median, mad = _algo_mad(candidates, mad_factor=6.0)
        assert flagged == []
        assert median == 5.0
        assert mad == 0.0

    def test_empty_input(self):
        flagged, median, mad = _algo_mad([], mad_factor=6.0)
        assert flagged == []
        assert median == 0.0
        assert mad == 0.0

    def test_flags_negative_spike(self):
        # With only 2 values the modified z-score is always 0.6745 (a constant),
        # so add enough normal data to give the algorithm a real baseline.
        normal = [_hour(i * 3_600_000, 1.0 + 0.1 * (i % 3 - 1)) for i in range(9)]
        spike = _hour(100 * 3_600_000, -1_000_000.0)
        candidates = normal + [spike]
        flagged, _, _ = _algo_mad(candidates, mad_factor=3.0)
        assert any(c.change == -1_000_000.0 for c in flagged)

    def test_mad_factor_sensitivity(self):
        # Lower factor → more aggressive; higher factor → fewer flags.
        candidates = self._make_varying_with_spike(50.0)
        aggressive, _, _ = _algo_mad(candidates, mad_factor=3.0)
        conservative, _, _ = _algo_mad(candidates, mad_factor=10.0)
        assert len(aggressive) >= len(conservative)


# ---------------------------------------------------------------------------
# _hybrid_rows
# ---------------------------------------------------------------------------


class TestHybridRows:
    def _make_hour(self, hour_idx: int, change: float = 1.0) -> OutlierCandidate:
        """Hour row: 3 600 000 ms wide."""
        start = hour_idx * 3_600_000
        return OutlierCandidate(
            start=start,
            end=start + 3_600_000,
            change=change,
            state=0.0,
            period="hour",
        )

    def _make_five_min_set(self, hour_idx: int, change_per_slot: float = 1.0 / 12) -> list[OutlierCandidate]:
        """12 five-minute rows filling one hour."""
        hour_start = hour_idx * 3_600_000
        rows = []
        for slot in range(12):
            start = hour_start + slot * 300_000
            rows.append(
                OutlierCandidate(
                    start=start,
                    end=start + 300_000,
                    change=change_per_slot,
                    state=0.0,
                    period="5minute",
                )
            )
        return rows

    def test_complete_hour_uses_five_min_samples(self):
        """Hour 0 has all 12 five-min samples → those 12 are used."""
        hour_rows = [self._make_hour(0)]
        five_min_rows = self._make_five_min_set(0)
        # Prepend a fake "first ever" row that gets dropped by hybrid_rows.
        five_min_rows = [_five_min(-300_000, 9999.0)] + five_min_rows

        result = _hybrid_rows(hour_rows, five_min_rows)

        assert len(result) == 12
        assert all(c.period == "5minute" for c in result)

    def test_incomplete_hour_uses_hourly_row(self):
        """Hour 0 has only 11 five-min samples → hourly row is used."""
        hour_rows = [self._make_hour(0)]
        five_min_rows = self._make_five_min_set(0)[:11]
        # Prepend dropped "first ever" row.
        five_min_rows = [_five_min(-300_000, 9999.0)] + five_min_rows

        result = _hybrid_rows(hour_rows, five_min_rows)

        assert len(result) == 1
        assert result[0].period == "hour"

    def test_first_five_min_row_is_always_dropped(self):
        """The very first 5-min sample is dropped per upstream convention."""
        hour_rows = [self._make_hour(0)]
        five_min_rows = self._make_five_min_set(0)
        # No extra prepended row: the first element of the list IS the "garbage" one.

        result = _hybrid_rows(hour_rows, five_min_rows)

        # Only 11 remain after the first is dropped → falls back to hourly.
        assert len(result) == 1
        assert result[0].period == "hour"

    def test_mixed_hours_complete_and_incomplete(self):
        """Hour 0 complete (uses 5min), hour 1 incomplete (uses hourly)."""
        hour_rows = [self._make_hour(0), self._make_hour(1)]

        # Hour 0: 12 samples (genuine) + 1 prepended "garbage" row to drop.
        hour0_five_min = self._make_five_min_set(0)
        garbage_row = _five_min(-300_000, 9999.0)

        # Hour 1: only 5 samples (partial).
        hour1_five_min = self._make_five_min_set(1)[:5]

        five_min_rows = [garbage_row] + hour0_five_min + hour1_five_min

        result = _hybrid_rows(hour_rows, five_min_rows)

        hour0_results = [c for c in result if c.start < 3_600_000]
        hour1_results = [c for c in result if c.start >= 3_600_000]

        assert len(hour0_results) == 12
        assert all(c.period == "5minute" for c in hour0_results)
        assert len(hour1_results) == 1
        assert hour1_results[0].period == "hour"

    def test_empty_five_min_returns_all_hourly(self):
        hour_rows = [self._make_hour(0), self._make_hour(1)]
        result = _hybrid_rows(hour_rows, [])
        assert len(result) == 2
        assert all(c.period == "hour" for c in result)

    def test_empty_both_returns_empty(self):
        assert _hybrid_rows([], []) == []
