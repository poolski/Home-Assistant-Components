# Statistics Outlier Cleaner

A Home Assistant custom integration for detecting and fixing outlier spikes in long-term statistics — the kind caused by HA restarts, meter replacements, or recorder compaction bugs.

Unlike the built-in Developer Tools > Statistics dialog, this integration:

- Fixes **both** `sum` and `state` columns, preventing spike re-injection after the next HA restart
- Supports **scheduled automation** via a service action (safe detection methods: MAD, absolute threshold)
- **Backs up** every affected row before mutating, with a one-click restore
- Handles the **bounded spike** pattern (a jump up followed by a compensating drop) by letting you select and fix both rows in one operation

> [!WARNING]
> This integration writes directly to the Home Assistant SQLite recorder database. It only supports SQLite (the default). MariaDB / PostgreSQL are not supported.

---

## Installation

### Via HACS (recommended)

1. Open HACS in your Home Assistant sidebar.
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**.
3. Add this repository URL and select category **Integration**.
4. Search for **Statistics Outlier Cleaner** and click **Download**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration** and search for **Statistics Outlier Cleaner**.

### Manual

1. Copy the `custom_components/statistics_outlier_cleaner` directory into your HA config folder so the path is:

   ```text
   <config>/custom_components/statistics_outlier_cleaner/
   ```

2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **Statistics Outlier Cleaner**.

---

## Usage

### Sidebar panel

After installation a new **Outlier Cleaner** entry appears in the sidebar (admin only).

1. Pick a statistic from the autocomplete picker (only sum-capable statistics are shown).
2. Select a date range.
3. Choose a detection method and click **Scan**.
4. Check the rows you want to fix (all are pre-selected). Set a replacement change value (default `0` removes the spike entirely).
5. Click **Apply Fix to Selected**. The fix is recorded in the history table below with its fix ID.
6. To undo, click **Restore** next to the relevant history entry.

### Service action

For scheduled or automation use, call `statistics_outlier_cleaner.clean_outliers`:

```yaml
action: statistics_outlier_cleaner.clean_outliers
data:
  statistic_id: sensor.electricity_meter_energy
  method: mad          # mad | absolute | top_n
  mad_factor: 6        # higher = more conservative
  period: hybrid       # hybrid | hour | 5minute
  lookback_days: 30    # 0 = all time
  replacement: 0       # set flagged change to this value
  dry_run: false
```

To restore a previous fix:

```yaml
action: statistics_outlier_cleaner.restore_fix
data:
  fix_id: "3f2504e0-4f89-11d3-9a0c-0305e82c3301"
```

The fix ID is logged at INFO level after every `clean_outliers` call.

---

## Detection methods

| Method | When to use | Safe for automation? |
| --- | --- | --- |
| `mad` | General-purpose. Flags rows whose [modified z-score](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm) ≥ `mad_factor`. Conservative: returns nothing when the sensor is flat. | ✅ Yes |
| `absolute` | You know the maximum plausible change (e.g. 100 kWh/h). Flags `\|change\| ≥ threshold`. | ✅ Yes |
| `top_n` | Matches the built-in dev tools behaviour. Always returns the N largest changes — will flag normal data if there are no real spikes. | ⚠️ Manual use only |

---

## How it works

Home Assistant stores long-term statistics in two SQLite tables:

- `statistics` — one row per hour (LTS)
- `statistics_short_term` — one row per 5 minutes (STS)

Each row has a cumulative `sum` and an instantaneous `state`. A spike manifests as a large `change` (= `sum[i] − sum[i−1]`) on one row.

When a fix is applied:

1. **Backup** — the spike row and all subsequent rows in both tables are copied to a backup table keyed by a `fix_id` UUID.
2. **Cascade** — `sum` is adjusted by `delta = replacement − change` on every row from the spike onwards (STS first, then LTS, to stay consistent with HA's own compilation order).
3. **State correction** — `state` on the spike row is set to `prev_state + replacement`, preserving the `sum − state` offset that existed before the spike. This prevents the spike from reappearing after the next HA restart.

To reverse: the backup rows are written back by row ID, then deleted from the backup table.

---

## Restart-hour spikes (bounded spikes)

The most common pattern is a jump **up** on the restart hour immediately followed by a compensating drop. Both rows should be selected together when applying a fix — the cascading deltas cancel out for all rows after the pair, leaving subsequent data unaffected.

---

## Requirements

- Home Assistant 2024.1 or later
- SQLite recorder (default)
- Admin access for the sidebar panel

---

## Limitations

- **SQLite only.** The direct database write path does not support MariaDB or PostgreSQL.
- **No chart.** The panel shows a table of flagged rows rather than a graph. Use the built-in Statistics developer tool to visualise before and after.
- The `top_n` method is intentionally excluded from the `clean_outliers` service to prevent accidental data loss in automations.
