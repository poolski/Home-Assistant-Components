/**
 * Statistics Outlier Cleaner — sidebar panel
 *
 * Vanilla web component, no build step required.
 * Uses native HTML controls for statistic selection and date range —
 * ha-statistic-picker and ha-date-range-picker are lazy-loaded by HA only
 * when the Statistics dev-tools view is opened, so they are never available
 * in a custom panel context.
 */

const DOMAIN = "statistics_outlier_cleaner";
const WS = {
  list_sum_statistics: `${DOMAIN}/list_sum_statistics`,
  fetch_outliers: `${DOMAIN}/fetch_outliers`,
  apply_fix: `${DOMAIN}/apply_fix`,
  list_fixes: `${DOMAIN}/list_fixes`,
  restore_fix: `${DOMAIN}/restore_fix`,
};

const STYLES = `
  :host {
    display: block;
    padding: 16px;
    font-family: var(--paper-font-body1_-_font-family, inherit);
    color: var(--primary-text-color);
    max-width: 1000px;
  }
  h2 { margin: 0 0 16px; font-size: 1.4rem; font-weight: 500; }
  h3 { margin: 0 0 12px; font-size: 1.1rem; font-weight: 500; }
  .card {
    background: var(--card-background-color, #fff);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
    box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,.1));
  }
  .form-row {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: flex-end;
    margin-bottom: 12px;
  }
  .form-group { display: flex; flex-direction: column; gap: 4px; }
  .form-group label {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--secondary-text-color);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  select, input[type=text], input[type=date], input[type=number] {
    padding: 8px 10px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 4px;
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color);
    font-size: 0.9rem;
    height: 40px;
    box-sizing: border-box;
  }
  select { min-width: 160px; }
  input[type=number] { width: 100px; }
  input[type=date] { width: 160px; }
  .stat-autocomplete {
    position: relative;
    flex: 1;
    min-width: 280px;
  }
  .stat-autocomplete input[type=text] {
    width: 100%;
    box-sizing: border-box;
  }
  .stat-autocomplete input[type=text].loading {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24'%3E%3Ccircle cx='12' cy='12' r='10' fill='none' stroke='%23ccc' stroke-width='3'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
  }
  .stat-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--card-background-color, #fff);
    border: 1px solid var(--divider-color, #e0e0e0);
    border-top: none;
    border-radius: 0 0 4px 4px;
    max-height: 220px;
    overflow-y: auto;
    z-index: 100;
    box-shadow: 0 4px 8px rgba(0,0,0,.1);
  }
  .stat-dropdown.hidden { display: none; }
  .stat-option {
    padding: 8px 10px;
    cursor: pointer;
    font-size: 0.875rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .stat-option:hover, .stat-option.active {
    background: rgba(var(--rgb-primary-color, 3,169,244), 0.1);
  }
  .stat-option.no-results {
    color: var(--secondary-text-color);
    cursor: default;
    font-style: italic;
  }
  button {
    padding: 0 16px;
    height: 36px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  button.primary { background: var(--primary-color, #03a9f4); color: #fff; }
  button.danger  { background: var(--error-color, #db4437); color: #fff; }
  button.secondary {
    background: transparent;
    color: var(--primary-color, #03a9f4);
    border: 1px solid var(--primary-color, #03a9f4);
  }
  button.text-btn {
    background: transparent;
    color: var(--primary-color, #03a9f4);
    padding: 0 8px;
    height: 28px;
    font-size: 0.8rem;
  }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  .hidden { display: none !important; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  th { font-weight: 500; background: var(--secondary-background-color, #f5f5f5); position: sticky; top: 0; }
  tr:hover td { background: rgba(var(--rgb-primary-color, 3,169,244), 0.05); }
  tr.selected td { background: rgba(var(--rgb-primary-color, 3,169,244), 0.1); }
  td.change-cell { font-family: monospace; }
  .status { padding: 10px 12px; border-radius: 6px; margin-bottom: 12px; font-size: 0.9rem; }
  .status.info    { background: #e3f2fd; color: #1565c0; }
  .status.success { background: #e8f5e9; color: #2e7d32; }
  .status.error   { background: #ffebee; color: #c62828; }
  .meta { font-size: 0.8rem; color: var(--secondary-text-color); margin-bottom: 10px; }
  .toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
  .selection-label { font-size: 0.85rem; color: var(--secondary-text-color); }
  .fix-controls { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .fix-controls label { font-size: 0.8rem; color: var(--secondary-text-color); }
  .dry-run-row { display: flex; align-items: center; gap: 6px; font-size: 0.875rem; cursor: pointer; }
  input[type=checkbox] { width: 16px; height: 16px; cursor: pointer; }
  .fix-id-chip {
    font-family: monospace;
    font-size: 0.75rem;
    background: var(--secondary-background-color, #f5f5f5);
    padding: 2px 6px;
    border-radius: 3px;
  }
`;

class StatisticsOutlierCleanerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._candidates = [];
    this._selected = new Set();
    this._msgId = 1;
    this._startDate = null;
    this._endDate = null;
    this._statId = null;
    this._allStats = [];      // full list from WS
    this._activeIdx = -1;     // keyboard nav index in dropdown
  }

  set hass(hass) {
    const firstSet = !this._hass;
    this._hass = hass;
    if (firstSet) {
      this._render();
      this._loadStatistics();
      this._loadHistory();
    }
  }

  // ---------------------------------------------------------------------------
  // Load statistics list for autocomplete
  // ---------------------------------------------------------------------------

  async _loadStatistics() {
    try {
      const result = await this._send({ type: WS.list_sum_statistics });
      this._allStats = (result.statistics || [])
        .map((s) => (typeof s === "string" ? s : s.statistic_id))
        .filter(Boolean)
        .sort();
    } catch (e) {
      this._allStats = [];
    }
  }

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------

  _defaultDateStr(offsetDays) {
    const d = new Date();
    d.setDate(d.getDate() + offsetDays);
    return d.toISOString().slice(0, 10);
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>

      <h2>Statistics Outlier Cleaner</h2>

      <div class="card">
        <h3>Scan</h3>

        <div class="form-row">
          <div class="form-group stat-autocomplete" id="stat-wrap">
            <label>Statistic</label>
            <input type="text" id="stat-input" placeholder="Type to search statistics…" autocomplete="off">
            <div class="stat-dropdown hidden" id="stat-dropdown"></div>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>From</label>
            <input type="date" id="date-start" value="${this._defaultDateStr(-30)}">
          </div>
          <div class="form-group">
            <label>To</label>
            <input type="date" id="date-end" value="${this._defaultDateStr(0)}">
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Detection method</label>
            <select id="method">
              <option value="mad">MAD — safe for automation</option>
              <option value="absolute">Absolute threshold</option>
              <option value="top_n">Top N (like dev tools)</option>
            </select>
          </div>
          <div class="form-group" id="opt-mad">
            <label>MAD factor</label>
            <input type="number" id="mad-factor" value="6" min="0.1" step="0.1">
          </div>
          <div class="form-group hidden" id="opt-absolute">
            <label>Threshold</label>
            <input type="number" id="threshold" value="100" min="0" step="0.001">
          </div>
          <div class="form-group hidden" id="opt-top-n">
            <label>Top N</label>
            <input type="number" id="top-n" value="10" min="1">
          </div>
        </div>

        <div class="form-row">
          <button class="primary" id="btn-scan">Scan</button>
        </div>
      </div>

      <div id="scan-status"></div>

      <div id="results-card" class="card hidden">
        <h3>Detected Outliers</h3>
        <div id="scan-meta" class="meta"></div>

        <div class="toolbar">
          <button class="text-btn" id="btn-select-all">Select all</button>
          <button class="text-btn" id="btn-select-none">Deselect all</button>
          <span class="selection-label" id="selection-count"></span>
        </div>

        <div id="results-table"></div>

        <div id="apply-area" class="hidden" style="margin-top:14px">
          <div class="fix-controls">
            <div class="form-group">
              <label>Replacement change</label>
              <input type="number" id="replacement" value="0" step="0.001">
            </div>
            <label class="dry-run-row">
              <input type="checkbox" id="dry-run">
              Dry run (no DB changes)
            </label>
            <button class="danger" id="btn-apply">Apply Fix to Selected</button>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>Fix History</h3>
        <button class="secondary" id="btn-refresh-history" style="margin-bottom:12px">Refresh</button>
        <div id="history-table"></div>
      </div>
    `;

    this._wireEvents();
  }

  _wireEvents() {
    this._q("method").addEventListener("change", () => this._updateMethodOptions());
    this._q("btn-scan").addEventListener("click", () => this._scan());
    this._q("btn-apply").addEventListener("click", () => this._applyFix());
    this._q("btn-select-all").addEventListener("click", () => this._selectAll(true));
    this._q("btn-select-none").addEventListener("click", () => this._selectAll(false));
    this._q("btn-refresh-history").addEventListener("click", () => this._loadHistory());

    const input = this._q("stat-input");
    input.addEventListener("input", () => this._onStatInput());
    input.addEventListener("keydown", (e) => this._onStatKeydown(e));
    input.addEventListener("focus", () => this._showDropdown(input.value));
    // Close dropdown when clicking outside
    document.addEventListener("click", (e) => {
      if (!this.shadowRoot.contains(e.target)) this._closeDropdown();
    });
  }

  _q(id) { return this.shadowRoot.getElementById(id); }

  _updateMethodOptions() {
    const m = this._q("method").value;
    this._q("opt-mad").classList.toggle("hidden", m !== "mad");
    this._q("opt-absolute").classList.toggle("hidden", m !== "absolute");
    this._q("opt-top-n").classList.toggle("hidden", m !== "top_n");
  }

  // ---------------------------------------------------------------------------
  // Statistic autocomplete
  // ---------------------------------------------------------------------------

  _onStatInput() {
    this._statId = null;   // clear confirmed selection while typing
    this._showDropdown(this._q("stat-input").value);
  }

  _showDropdown(filter) {
    const dd = this._q("stat-dropdown");
    const term = filter.trim().toLowerCase();
    const matches = term
      ? this._allStats.filter((s) => s.toLowerCase().includes(term))
      : this._allStats;

    if (!matches.length) {
      dd.innerHTML = `<div class="stat-option no-results">${
        this._allStats.length ? "No matches" : "Loading statistics…"
      }</div>`;
    } else {
      dd.innerHTML = matches.slice(0, 50).map((s) =>
        `<div class="stat-option" data-value="${s}">${s}</div>`
      ).join("");
      dd.querySelectorAll(".stat-option[data-value]").forEach((el) => {
        el.addEventListener("mousedown", (e) => {
          e.preventDefault();
          this._selectStat(el.dataset.value);
        });
      });
    }

    this._activeIdx = -1;
    dd.classList.remove("hidden");
  }

  _onStatKeydown(e) {
    const dd = this._q("stat-dropdown");
    const options = [...dd.querySelectorAll(".stat-option[data-value]")];
    if (e.key === "ArrowDown") {
      e.preventDefault();
      this._activeIdx = Math.min(this._activeIdx + 1, options.length - 1);
      this._highlightOption(options);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      this._activeIdx = Math.max(this._activeIdx - 1, 0);
      this._highlightOption(options);
    } else if (e.key === "Enter" && this._activeIdx >= 0) {
      e.preventDefault();
      this._selectStat(options[this._activeIdx].dataset.value);
    } else if (e.key === "Escape") {
      this._closeDropdown();
    }
  }

  _highlightOption(options) {
    options.forEach((el, i) => el.classList.toggle("active", i === this._activeIdx));
    options[this._activeIdx]?.scrollIntoView({ block: "nearest" });
  }

  _selectStat(value) {
    this._statId = value;
    this._q("stat-input").value = value;
    this._closeDropdown();
  }

  _closeDropdown() {
    this._q("stat-dropdown")?.classList.add("hidden");
  }

  // ---------------------------------------------------------------------------
  // WS helpers
  // ---------------------------------------------------------------------------

  _send(msg) {
    return this._hass.connection.sendMessagePromise({ id: this._msgId++, ...msg });
  }

  // ---------------------------------------------------------------------------
  // Scan
  // ---------------------------------------------------------------------------

  async _scan() {
    const statId = this._statId || this._q("stat-input").value.trim();
    if (!statId) { this._showStatus("error", "Select a statistic first."); return; }

    const method = this._q("method").value;
    const startVal = this._q("date-start").value;
    const endVal   = this._q("date-end").value;

    const params = {
      type: WS.fetch_outliers,
      statistic_id: statId,
      period: "hybrid",
      method,
    };

    if (startVal) {
      const startMs = new Date(startVal).getTime();
      params.lookback_days = Math.ceil((Date.now() - startMs) / 86_400_000);
    }

    if (method === "mad")      params.mad_factor = parseFloat(this._q("mad-factor").value) || 6;
    if (method === "absolute") params.threshold  = parseFloat(this._q("threshold").value) || 0;
    if (method === "top_n")    params.top_n      = parseInt(this._q("top-n").value) || 10;

    this._showStatus("info", "Scanning…");
    this._q("btn-scan").disabled = true;

    try {
      const result = await this._send(params);
      this._candidates = result.candidates || [];
      this._selected = new Set(this._candidates.map((_, i) => i));
      this._renderResults(result);
      this._clearStatus();
    } catch (e) {
      this._showStatus("error", `Scan failed: ${e.message || JSON.stringify(e)}`);
    } finally {
      this._q("btn-scan").disabled = false;
    }

    this._loadHistory();
  }

  _renderResults(report) {
    const card = this._q("results-card");
    card.classList.remove("hidden");

    this._q("scan-meta").textContent =
      `Scanned ${report.scanned_rows} rows · Method: ${report.method}` +
      (report.median != null ? ` · Median: ${report.median.toFixed(4)}` : "") +
      (report.mad    != null ? ` · MAD: ${report.mad.toFixed(4)}`       : "");

    if (!this._candidates.length) {
      this._q("results-table").innerHTML = "<p>No outliers detected.</p>";
      this._q("apply-area").classList.add("hidden");
      this._updateSelectionCount();
      return;
    }

    this._renderTable();
    this._q("apply-area").classList.remove("hidden");
  }

  _renderTable() {
    const tbody = this._candidates.map((c, i) => {
      const dt = new Date(c.start).toLocaleString();
      const checked = this._selected.has(i) ? "checked" : "";
      return `<tr class="${this._selected.has(i) ? "selected" : ""}" data-idx="${i}">
        <td><input type="checkbox" class="row-check" data-idx="${i}" ${checked}></td>
        <td>${dt}</td>
        <td>${c.period}</td>
        <td class="change-cell">${c.change.toFixed(4)}</td>
        <td>${c.state != null ? c.state.toFixed(4) : "—"}</td>
      </tr>`;
    }).join("");

    this._q("results-table").innerHTML = `
      <table>
        <thead>
          <tr>
            <th style="width:32px"><input type="checkbox" id="check-all" ${
              this._selected.size === this._candidates.length ? "checked" : ""
            }></th>
            <th>Start</th><th>Period</th><th>Change</th><th>State</th>
          </tr>
        </thead>
        <tbody>${tbody}</tbody>
      </table>`;

    this._q("check-all").addEventListener("change", (e) => this._selectAll(e.target.checked));
    this._q("results-table").querySelectorAll(".row-check").forEach((cb) => {
      cb.addEventListener("change", (e) => {
        const idx = parseInt(e.target.dataset.idx);
        e.target.checked ? this._selected.add(idx) : this._selected.delete(idx);
        this._q("results-table").querySelector(`tr[data-idx="${idx}"]`)
          ?.classList.toggle("selected", e.target.checked);
        this._updateSelectionCount();
        this._updateCheckAll();
      });
    });

    this._updateSelectionCount();
  }

  _selectAll(on) {
    if (on) this._candidates.forEach((_, i) => this._selected.add(i));
    else this._selected.clear();
    this._renderTable();
  }

  _updateSelectionCount() {
    const n = this._selected.size, total = this._candidates.length;
    this._q("selection-count").textContent = n ? `${n} of ${total} selected` : "";
    this._q("btn-apply").disabled = n === 0;
  }

  _updateCheckAll() {
    const cb = this._q("check-all");
    if (!cb) return;
    cb.checked = this._selected.size === this._candidates.length;
    cb.indeterminate = this._selected.size > 0 && this._selected.size < this._candidates.length;
  }

  // ---------------------------------------------------------------------------
  // Apply fix
  // ---------------------------------------------------------------------------

  async _applyFix() {
    if (!this._selected.size) return;

    const statId = this._statId || this._q("stat-input").value.trim();
    const replacement = parseFloat(this._q("replacement").value) || 0;
    const dryRun = this._q("dry-run").checked;

    const candidates = [...this._selected].map((i) => ({
      start_ts: this._candidates[i].start / 1000,
      period: this._candidates[i].period,
    }));

    this._showStatus("info", dryRun ? "Running dry-run…" : "Applying fix…");
    this._q("btn-apply").disabled = true;

    try {
      const result = await this._send({
        type: WS.apply_fix,
        statistic_id: statId,
        candidates,
        replacement,
        dry_run: dryRun,
      });

      const hasErrors = result.errors?.length > 0;
      const msg = dryRun
        ? `Dry run: would fix ${result.planned} row(s).`
        : `Fixed ${result.applied} row(s). Fix ID: <span class="fix-id-chip">${result.fix_id}</span>`;
      this._showStatus(hasErrors ? "error" : "success", msg);

      if (!dryRun) {
        const removed = new Set(this._selected);
        this._candidates = this._candidates.filter((_, i) => !removed.has(i));
        this._selected = new Set(this._candidates.map((_, i) => i));
        if (this._candidates.length) {
          this._renderTable();
        } else {
          this._q("results-table").innerHTML = "<p>No outliers remaining.</p>";
          this._q("apply-area").classList.add("hidden");
        }
        this._loadHistory();
      }
    } catch (e) {
      this._showStatus("error", `Apply failed: ${e.message || JSON.stringify(e)}`);
    } finally {
      if (this._selected.size) this._q("btn-apply").disabled = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Fix history
  // ---------------------------------------------------------------------------

  async _loadHistory() {
    try {
      const result = await this._send({ type: WS.list_fixes, limit: 20 });
      this._renderHistory(result.fixes || []);
    } catch (e) {
      this._q("history-table").innerHTML =
        `<p style="color:var(--error-color)">Failed to load history: ${e.message || e}</p>`;
    }
  }

  _renderHistory(fixes) {
    const div = this._q("history-table");
    if (!fixes.length) { div.innerHTML = "<p>No fixes recorded yet.</p>"; return; }

    const rows = fixes.map((f) => {
      const dt = new Date(f.fix_ts * 1000).toLocaleString();
      return `<tr>
        <td>${dt}</td>
        <td><span class="fix-id-chip">${f.fix_id.slice(0, 8)}…</span></td>
        <td>${f.statistic_id}</td>
        <td>${f.row_count}</td>
        <td><button class="text-btn restore-btn" data-fix-id="${f.fix_id}">Restore</button></td>
      </tr>`;
    }).join("");

    div.innerHTML = `
      <table>
        <thead><tr><th>Date</th><th>Fix ID</th><th>Sensor</th><th>Rows</th><th></th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;

    div.querySelectorAll(".restore-btn").forEach((btn) => {
      btn.addEventListener("click", () => this._restoreFix(btn.dataset.fixId));
    });
  }

  async _restoreFix(fixId) {
    if (!confirm(`Restore fix ${fixId.slice(0, 8)}…? This will revert the database changes.`)) return;
    this._showStatus("info", "Restoring…");
    try {
      const result = await this._send({ type: WS.restore_fix, fix_id: fixId });
      this._showStatus("success", `Restored ${result.restored} row(s).`);
      this._loadHistory();
    } catch (e) {
      this._showStatus("error", `Restore failed: ${e.message || JSON.stringify(e)}`);
    }
  }

  // ---------------------------------------------------------------------------
  // Status helpers
  // ---------------------------------------------------------------------------

  _showStatus(type, msg) {
    this._q("scan-status").innerHTML = `<div class="status ${type}">${msg}</div>`;
  }

  _clearStatus() { this._q("scan-status").innerHTML = ""; }
}

customElements.define("statistics-outlier-cleaner-panel", StatisticsOutlierCleanerPanel);
