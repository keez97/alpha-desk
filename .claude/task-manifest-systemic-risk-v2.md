# Task Manifest: Systemic Risk Engine V2

## Objective
Overhaul the systemic risk calculation in `backend/services/regime_detector.py` to match
institutional-grade standards from the Kritzman/Windham Capital literature. Extract core
systemic risk math into a dedicated module, expand asset universes, improve covariance
estimation, and wire improved signals into downstream consumers.

## Research Summary (from articles + papers)

### Absorption Ratio (Kritzman, Li, Page & Rigobon 2011)
- Formula: AR = Σ(σ²_top_eigenvectors) / Σ(σ²_all_assets)
- Canonical universe: **11 Sector SPDR ETFs** (XLK, XLV, XLF, XLY, XLP, XLE, XLRE, XLI, XLU, XLC, XLB)
- Retain **N/5 eigenvectors** (≈2 for 11 assets)
- Use **weekly returns** with **52-week rolling window**
- Track **AR delta** (week-over-week change) as leading indicator
- Use **Ledoit-Wolf shrinkage** for covariance estimation at scale

### Turbulence Index (Chow et al. 1999, Kritzman & Li 2010)
- Formula: d_t = (1/n)(r_t - μ)^T Σ^{-1} (r_t - μ)
- Recommended universe: **7-10 cross-asset class ETFs**
- Use **rolling 60-day window** for reference distribution (not full-period)
- n*d_t follows **chi-squared(n)** under null → compute p-value
- Use **Ledoit-Wolf shrinkage** for covariance inversion stability

### Windham 2x2 Framework
- Replace binary thresholds with **smooth sigmoid transitions**
- Add **state persistence weighting** (consecutive periods in state)
- Keep hysteresis (already implemented in commit 726968b)

---

## Current Implementation (what exists)

### File: `backend/services/regime_detector.py`
- `MULTI_ASSET_TICKERS = ["SPY", "TLT", "GLD", "HYG"]` (only 4 assets)
- `_fetch_multi_asset_returns("1y")` → fetches 1 year daily via yahoo_direct
- `_compute_turbulence_index(returns)` → full-period μ/Σ, raw np.cov, np.linalg.inv
- `_compute_absorption_ratio(returns, n_components=1)` → 60-day rolling, 1 eigenvector, raw np.cov
- `_windham_fragility_state(turb_pctile, ar_pctile)` → binary thresholds with hysteresis
- `_compute_systemic_layer()` → orchestrates above, feeds into Windham classification

### Data already flowing in the app:
- `yfinance_service.py` line 236-245: sector_etfs dict with all 11 Sector SPDRs
- `yfinance_service.py` line 181: macro tickers including ^TNX, DX-Y.NYB, GC=F, CL=F, BTC-USD
- `cross_asset_momentum.py`: SPY, TLT, GLD, USO, UUP, BTC-USD
- `yahoo_direct.get_history(ticker, range_str, interval)`: works for all of these

### Downstream consumers to wire into:
- `rotation_alert_engine.py`: RRG-based rotation alerts, can use AR delta for timing
- `cot_positioning.py`: COT extremes, can cross-ref with Windham state
- `smart_analysis.py`: Morning report, already reads regime dict
- `confluence_engine.py`: Signal confluence, reads regime

---

## Agent Assignments

### AGENT 1: Core Systemic Risk Engine Builder
**Priority**: P0 + P1 + P2
**File scope**:
  - CREATE: `backend/services/systemic_risk_engine.py` (new module)
  - MODIFY: `backend/services/regime_detector.py` (import from new module)

**Tasks**:
1. Create `backend/services/systemic_risk_engine.py` with:
   a. `SECTOR_ETF_UNIVERSE` — 11 Sector SPDRs for absorption ratio
   b. `CROSS_ASSET_UNIVERSE` — 10 cross-asset ETFs for turbulence
   c. `fetch_sector_returns(lookback_weeks=52)` → weekly returns matrix
   d. `fetch_cross_asset_returns(lookback_days=252)` → daily returns matrix
   e. `compute_absorption_ratio(weekly_returns, n_components=2)` → AR, AR_delta, percentile, series
      - Ledoit-Wolf covariance shrinkage via sklearn
      - 52-week rolling window of weekly returns
      - Returns AR delta (current - previous week)
   f. `compute_turbulence_index(daily_returns, window=60)` → turbulence, percentile, p_value, series
      - Rolling 60-day window for μ and Σ
      - Ledoit-Wolf shrinkage for Σ inversion
      - Chi-squared p-value: n*d_t ~ χ²(n)
   g. `classify_windham_state(turb_pctile, ar_pctile, ar_delta, prev_state)` → state dict
      - Smooth sigmoid transitions (no hard binary thresholds)
      - State persistence tracking (consecutive_periods counter)
      - AR delta early warning flag
      - Hysteresis preserved from commit 726968b

2. Update `regime_detector.py`:
   a. Replace `_fetch_multi_asset_returns`, `_compute_turbulence_index`,
      `_compute_absorption_ratio`, `_windham_fragility_state` with imports from new module
   b. Update `_compute_systemic_layer()` to call new module functions
   c. Add new fields to output dict: `ar_delta`, `turbulence_p_value`,
      `windham_persistence_periods`, `ar_delta_warning`
   d. Preserve existing hysteresis constants and override logic

**Acceptance criteria**:
- `pip install scikit-learn --break-system-packages` succeeds
- AR computed from 11 sector ETFs with 2 eigenvectors
- Turbulence computed from 10 cross-asset ETFs with rolling window
- Ledoit-Wolf used for both covariance matrices
- Chi-squared p-value reported alongside turbulence percentile
- AR delta (weekly change) computed and exposed
- Windham states use sigmoid transitions, not hard binary
- All existing regime_detector tests still pass
- New module has its own unit tests validating math against known values

### AGENT 2: Downstream Wiring Builder
**Priority**: P3
**File scope**:
  - MODIFY: `backend/services/rotation_alert_engine.py`
  - MODIFY: `backend/services/cot_positioning.py`
  - MODIFY: `backend/services/smart_analysis.py` (only systemic risk narrative section)

**Tasks**:
1. `rotation_alert_engine.py`:
   - Add method `inject_systemic_context(regime_data: dict)` that accepts the regime
     detector output
   - When AR delta > 1 std dev increase AND sector is rotating INTO "Leading" quadrant,
     add a warning flag: "Caution: systemic coupling rising — rotation may reverse"
   - When AR delta < -1 std dev decrease AND sector rotating into "Improving",
     add confidence boost: "Systemic decorrelation supports rotation thesis"

2. `cot_positioning.py`:
   - Add method `cross_reference_windham(market_data: dict, windham_state: str)`
   - When specs are extreme long (>90th pctile) AND windham_state is "fragile-calm"
     or "fragile-turbulent", flag: "DANGER: Speculative crowding in fragile market"
   - When commercials are extreme long AND windham_state is "fragile-calm",
     flag: "Smart money hedging in hidden risk environment"

3. `smart_analysis.py`:
   - Update the systemic risk narrative section (around line 467-508) to include:
     - AR delta context ("Absorption ratio rose/fell X% this week")
     - Turbulence p-value context ("Statistically significant at p=X")
     - Persistence context ("Market has been in X state for Y weeks")

**Acceptance criteria**:
- New methods callable from existing endpoints
- No breaking changes to existing function signatures
- Cross-reference logic produces meaningful alerts on real data

### AGENT 3: Mathematical Validator (Read-Only)
**Priority**: Validation
**File scope**: READ-ONLY (no file modifications)

**Tasks**:
1. Validate absorption ratio formula against Kritzman (2011):
   - Verify eigenvector count (N/5 rule)
   - Verify rolling window approach matches paper
   - Verify AR delta computation is correct

2. Validate turbulence index formula against Kritzman & Li (2010):
   - Verify Mahalanobis distance formula: d_t = (1/n)(r_t - μ)^T Σ^{-1} (r_t - μ)
   - Verify rolling window vs full-period approach
   - Verify chi-squared calibration: n*d_t ~ χ²(n) degrees of freedom

3. Validate Ledoit-Wolf application:
   - Confirm sklearn LedoitWolf is appropriate for this use case
   - Verify shrinkage applies before PCA for AR and before inversion for turbulence

4. Validate sigmoid transition math:
   - Verify sigmoid parameters produce sensible transition behavior
   - Confirm thresholds approximate binary behavior at extremes

5. Cross-check with known historical crises:
   - Verify that on 2020-03 (COVID crash) data, the model would produce
     fragile-turbulent classification
   - Verify 2008 financial crisis pattern matches literature

**Output**: Report listing each formula check as PASS/FAIL with reasoning.
