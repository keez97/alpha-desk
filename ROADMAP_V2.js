const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber, PageBreak, TabStopType, TabStopPosition,
  ExternalHyperlink
} = require("docx");

// ─── DESIGN TOKENS ───
const BRAND = "1B3A5C";
const ACCENT = "2E75B6";
const DARK = "1A1A1A";
const MID = "555555";
const LIGHT = "888888";
const BG_HEADER = "1B3A5C";
const BG_ALT = "F5F7FA";
const BORDER_CLR = "D0D5DD";
const WHITE = "FFFFFF";

const thinBorder = { style: BorderStyle.SINGLE, size: 1, color: BORDER_CLR };
const borders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };
const noBorders = {
  top: { style: BorderStyle.NONE, size: 0 },
  bottom: { style: BorderStyle.NONE, size: 0 },
  left: { style: BorderStyle.NONE, size: 0 },
  right: { style: BorderStyle.NONE, size: 0 },
};

// ─── HELPERS ───
function heading(text, level = HeadingLevel.HEADING_1) {
  return new Paragraph({ heading: level, spacing: { before: level === HeadingLevel.HEADING_1 ? 360 : 240, after: 160 }, children: [new TextRun({ text, bold: true, font: "Arial", size: level === HeadingLevel.HEADING_1 ? 32 : level === HeadingLevel.HEADING_2 ? 26 : 22, color: BRAND })] });
}

function body(text, opts = {}) {
  return new Paragraph({ spacing: { after: 120, line: 276 }, ...opts, children: [new TextRun({ text, font: "Arial", size: 21, color: DARK })] });
}

function bodyRuns(runs, opts = {}) {
  return new Paragraph({ spacing: { after: 120, line: 276 }, ...opts, children: runs.map(r => new TextRun({ font: "Arial", size: 21, color: DARK, ...r })) });
}

function bullet(text, ref = "bullets", level = 0) {
  return new Paragraph({ numbering: { reference: ref, level }, spacing: { after: 80, line: 276 }, children: [new TextRun({ text, font: "Arial", size: 21, color: DARK })] });
}

function bulletRuns(runs, ref = "bullets", level = 0) {
  return new Paragraph({ numbering: { reference: ref, level }, spacing: { after: 80, line: 276 }, children: runs.map(r => new TextRun({ font: "Arial", size: 21, color: DARK, ...r })) });
}

function numbered(text, ref = "numbers", level = 0) {
  return new Paragraph({ numbering: { reference: ref, level }, spacing: { after: 80, line: 276 }, children: [new TextRun({ text, font: "Arial", size: 21, color: DARK })] });
}

function numberedRuns(runs, ref = "numbers", level = 0) {
  return new Paragraph({ numbering: { reference: ref, level }, spacing: { after: 80, line: 276 }, children: runs.map(r => new TextRun({ font: "Arial", size: 21, color: DARK, ...r })) });
}

function spacer(h = 120) {
  return new Paragraph({ spacing: { after: h }, children: [] });
}

function headerCell(text, width) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    shading: { fill: BG_HEADER, type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, font: "Arial", size: 18, color: WHITE })] })]
  });
}

function dataCell(text, width, opts = {}) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    shading: opts.shading ? { fill: opts.shading, type: ShadingType.CLEAR } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    verticalAlign: "center",
    children: [new Paragraph({ children: [new TextRun({ text, font: "Arial", size: 18, color: opts.color || DARK, bold: opts.bold || false })] })]
  });
}

function makeTable(headers, rows, colWidths) {
  const totalWidth = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({ children: headers.map((h, i) => headerCell(h, colWidths[i])) }),
      ...rows.map((row, ri) => new TableRow({
        children: row.map((cell, ci) => {
          if (typeof cell === "object" && cell.text !== undefined) {
            return dataCell(cell.text, colWidths[ci], { shading: ri % 2 === 1 ? BG_ALT : undefined, ...cell });
          }
          return dataCell(cell, colWidths[ci], { shading: ri % 2 === 1 ? BG_ALT : undefined });
        })
      }))
    ]
  });
}

// ─── BUILD THE DOCUMENT ───

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: BRAND },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: BRAND },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: ACCENT },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1440, hanging: 360 } } } },
      ]},
      { reference: "numbers", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.LOWER_LETTER, text: "%2.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1440, hanging: 360 } } } },
      ]},
      { reference: "numbers2", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      ]},
      { reference: "numbers3", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      ]},
      { reference: "numbers4", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      ]},
    ]
  },
  sections: [
    // ══════════════════════════════════════════════════════════
    // COVER PAGE
    // ══════════════════════════════════════════════════════════
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      children: [
        spacer(2400),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [
          new TextRun({ text: "ALPHADESK", font: "Arial", size: 56, bold: true, color: BRAND })
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [
          new TextRun({ text: "Alpha Generation Roadmap", font: "Arial", size: 36, color: MID })
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 }, children: [
          new TextRun({ text: "Implementation Plan for V2 Feature Suite", font: "Arial", size: 24, color: LIGHT })
        ]}),
        spacer(600),
        new Paragraph({ alignment: AlignmentType.CENTER, border: { top: { style: BorderStyle.SINGLE, size: 2, color: ACCENT, space: 8 } }, spacing: { before: 200, after: 100 }, children: [
          new TextRun({ text: "March 2026  |  Confidential", font: "Arial", size: 20, color: LIGHT })
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 }, children: [
          new TextRun({ text: "Prepared for Karim Atari", font: "Arial", size: 20, color: MID })
        ]}),
      ]
    },

    // ══════════════════════════════════════════════════════════
    // EXECUTIVE SUMMARY + BUILD ORDER
    // ══════════════════════════════════════════════════════════
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1080, left: 1440 }
        }
      },
      headers: {
        default: new Header({ children: [new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: BORDER_CLR, space: 4 } },
          children: [
            new TextRun({ text: "ALPHADESK  ", font: "Arial", size: 16, bold: true, color: BRAND }),
            new TextRun({ text: "Alpha Generation Roadmap", font: "Arial", size: 16, color: LIGHT }),
          ],
          tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
        })] })
      },
      footers: {
        default: new Footer({ children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "Confidential  |  Page ", font: "Arial", size: 16, color: LIGHT }),
            new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: LIGHT }),
          ]
        })] })
      },
      children: [
        heading("Executive Summary"),
        body("This document outlines the implementation plan for four major alpha-generation features that will transform AlphaDesk from a market monitoring dashboard into a research-grade investment terminal. Each feature is grounded in peer-reviewed academic research and proven institutional methodologies."),
        spacer(80),
        bodyRuns([
          { text: "The build order follows the priority sequencing recommended in the attached research report, beginning with the ", },
          { text: "Factor Backtester", bold: true },
          { text: " (heaviest infrastructure, enables validation of all other signals), followed by the " },
          { text: "Event Scanner", bold: true },
          { text: " (leverages EDGAR and news APIs for real-time alpha), then the " },
          { text: "Earnings Surprise Predictor", bold: true },
          { text: " (strongest academic backing at 70%+ directional accuracy), and finally " },
          { text: "News Sentiment Scoring", bold: true },
          { text: " (AI-powered contrarian signal detection)." },
        ]),
        spacer(80),

        heading("Build Order and Timeline", HeadingLevel.HEADING_2),
        makeTable(
          ["Phase", "Feature", "Key Deliverable", "Academic Basis"],
          [
            ["Phase 1", "Factor Backtester", "Walk-forward backtesting engine with PiT data, Fama-French 5-factor framework, survivorship-bias-free universe", "FactSet PiT methodology; Fama-French (1993/2015); Look-Ahead-Bench (2026)"],
            ["Phase 2", "Event Scanner", "Real-time event detection from EDGAR filings, news APIs, and options flow with alpha decay tracking", "Lu et al. (ACL 2021) event detection; 13D filing alpha (6.33% avg); PEAD literature"],
            ["Phase 3", "Earnings Surprise Predictor", "SmartEstimate engine with analyst weighting by recency, accuracy, and broker size", "StarMine (70% directional accuracy); SSRN 2007 analyst weighting; Bernard & Thomas (1989) PEAD"],
            ["Phase 4", "News Sentiment Scoring", "FinBERT + Loughran-McDonald pipeline with sentiment velocity and contrarian divergence alerts", "Araci (2019) FinBERT; Stanford CS224N NLP study; L-M Dictionary (Notre Dame SRAF)"],
          ],
          [1200, 1800, 3400, 2960]
        ),

        spacer(160),
        heading("Cross-Cutting Data Infrastructure", HeadingLevel.HEADING_2),
        body("All four features share foundational infrastructure requirements identified in Section 4 of the research report. These must be built first as a shared data layer:"),
        spacer(40),
        makeTable(
          ["Requirement", "Implementation", "Why It Matters"],
          [
            ["Point-in-Time (PiT) Database", "Timestamp all data ingestion; never overwrite historical values; use Input Date (date collected) not Research Date", "Without PiT, backtests show 15-25% inflated Sharpe ratios (FactSet white paper). Strategies appear profitable but fail live."],
            ["Survivorship-Bias-Free Universe", "Include all delisted, acquired, and bankrupt securities with full price history; track index membership over time", "Excluding delistings can 4x inflate backtested returns (Quantified Strategies). This is the most common error in retail backtesting."],
            ["Look-Ahead Bias Prevention", "Enforce strict temporal ordering in all feature construction; no future data in training or signal generation", "Look-Ahead-Bench (Jan 2026) demonstrates that even LLMs exhibit significant look-ahead bias in financial workflows."],
            ["Consensus Estimate History", "Store individual analyst estimates with timestamps, not just current consensus snapshot", "Informed weighting by forecast age, analyst accuracy, and broker size reduces MSE by 3-15% vs equal-weighted consensus (SSRN 2007)."],
          ],
          [2000, 3500, 3860]
        ),

        // ══════════════════════════════════════════════════════════
        // PHASE 1: FACTOR BACKTESTER
        // ══════════════════════════════════════════════════════════
        new Paragraph({ children: [new PageBreak()] }),
        heading("Phase 1: Factor Backtester"),
        bodyRuns([
          { text: "The Factor Backtester is the highest-infrastructure feature but provides the quantitative foundation for validating every other signal in the system. It lets users define multi-factor models, run historical backtests with proper bias controls, and measure factor performance with institutional-grade statistics." },
        ]),

        heading("1.1 Scientific Foundation", HeadingLevel.HEADING_2),
        bodyRuns([
          { text: "The Fama-French five-factor model", bold: true },
          { text: " explains over 90% of return variability (vs ~70% for CAPM alone). The five factors are: MKT-RF (market excess return), SMB (small minus big), HML (high minus low book-to-market), RMW (robust minus weak profitability), and CMA (conservative minus aggressive investment). Research shows factor effectiveness is " },
          { text: "not stable across time or countries", italics: true },
          { text: " (arXiv 2024), arguing for rolling-window regressions rather than full-sample estimates." },
        ]),
        spacer(40),
        bodyRuns([
          { text: "Critical insight from the research: ", bold: true },
          { text: "a December 2025 paper provides a game-theoretic model showing that factor alpha decays post-publication. Mechanical factors (size, value) decay faster than judgment factors (quality, momentum) because ETF crowding accelerates arbitrage. Users should expect live performance to be approximately 50% of historical backtested returns for published factors." },
        ]),

        heading("1.2 Backend Architecture", HeadingLevel.HEADING_2),
        heading("Data Layer", HeadingLevel.HEADING_3),
        numbered("New SQLModel tables: FactorUniverse (ticker, date, is_active, delisted_date), FactorData (ticker, date, factor_name, factor_value, ingestion_timestamp), BacktestRun (id, config_json, created_at, status), BacktestResult (run_id, date, portfolio_return, benchmark_return, factor_exposures_json)."),
        numbered("Point-in-Time enforcement: every row gets an ingestion_timestamp. Queries for date D only return rows where ingestion_timestamp <= D. This prevents look-ahead bias at the database level."),
        numbered("Data sources: yfinance for price history (already integrated), Kenneth French Data Library for factor returns (free, CSV download), SEC EDGAR for fundamental data snapshots."),

        heading("Factor Construction Engine", HeadingLevel.HEADING_3),
        bodyRuns([
          { text: "New service: " },
          { text: "backend/services/factor_engine.py", bold: true },
        ]),
        bullet("Compute Fama-French factors from raw price and fundamental data using the standard double-sort methodology: sort stocks into 2x3 portfolios on size (market cap) and value (B/M ratio), then compute factor returns as the difference between portfolio groups."),
        bullet("Support custom factors: users define a factor as any numeric function of fundamentals (e.g., FCF yield = free_cash_flow / market_cap). The engine ranks stocks by factor value, constructs long-short quintile portfolios, and computes factor returns."),
        bullet("Rolling-window factor regressions: 60-month rolling windows for monthly factor returns, with configurable window size. Report both in-sample and out-of-sample performance separately."),

        heading("Backtesting Engine", HeadingLevel.HEADING_3),
        bodyRuns([
          { text: "New service: " },
          { text: "backend/services/backtester.py", bold: true },
        ]),
        numbered("Walk-forward protocol: at each rebalance date, use only data available up to that date. Re-optimize factor weights using trailing window. Generate forward portfolio. Step forward and repeat.", "numbers2"),
        numbered("Portfolio construction: sort universe into quantile portfolios (quintiles or deciles) based on composite factor score. Long top quantile, short bottom quantile (or long-only mode). Equal-weight within each quantile.", "numbers2"),
        numbered("Transaction cost modeling: configurable slippage (default 10bps one-way), commission structure, and market impact estimation for small-cap names.", "numbers2"),
        numbered("Rebalance frequencies: monthly, quarterly, or custom. Track turnover rate per rebalance.", "numbers2"),

        heading("Statistical Output", HeadingLevel.HEADING_3),
        body("For each backtest run, compute and store:"),
        makeTable(
          ["Metric", "Formula / Method", "Why"],
          [
            ["Annualized Return", "Geometric mean of period returns x periods/year", "Core performance measure"],
            ["Annualized Volatility", "Std dev of returns x sqrt(periods/year)", "Risk measure"],
            ["Sharpe Ratio", "(Return - Rf) / Volatility", "Risk-adjusted performance"],
            ["Sortino Ratio", "(Return - Rf) / Downside Deviation", "Penalizes downside only"],
            ["Maximum Drawdown", "Largest peak-to-trough decline", "Worst-case loss"],
            ["Calmar Ratio", "Annualized Return / Max Drawdown", "Return per unit of drawdown risk"],
            ["Information Ratio", "Active Return / Tracking Error", "Alpha per unit of active risk"],
            ["Factor Exposures", "Rolling regression betas to FF5 factors", "Attribution of returns to known factors"],
            ["Turnover", "Sum of absolute weight changes / 2", "Trading cost proxy"],
            ["Hit Rate", "% of periods with positive return", "Consistency measure"],
            ["Pre vs Post-Publication", "Split performance at factor publication date", "Alpha decay measurement per Dec 2025 paper"],
          ],
          [2200, 4000, 3160]
        ),

        heading("1.3 API Endpoints", HeadingLevel.HEADING_2),
        makeTable(
          ["Method", "Endpoint", "Description"],
          [
            ["POST", "/api/backtest/run", "Submit a backtest configuration (factors, weights, universe, date range, rebalance freq, transaction costs)"],
            ["GET", "/api/backtest/{id}", "Retrieve backtest results including equity curve, statistics, and factor exposures"],
            ["GET", "/api/backtest/history", "List all saved backtest runs with summary stats"],
            ["GET", "/api/factors/library", "List available pre-built factors (FF5 + custom) with descriptions"],
            ["POST", "/api/factors/custom", "Define a new custom factor from fundamentals"],
            ["GET", "/api/factors/{name}/returns", "Get historical factor return series"],
            ["DELETE", "/api/backtest/{id}", "Delete a saved backtest run"],
          ],
          [1000, 3000, 5360]
        ),

        heading("1.4 Frontend Components", HeadingLevel.HEADING_2),
        bodyRuns([
          { text: "New page: " },
          { text: "/backtester", bold: true },
          { text: " accessible from TopNav. The page layout follows our established pattern: sidebar for configuration, main area for results." },
        ]),
        spacer(40),
        bulletRuns([{ text: "Factor Selection Panel (sidebar): ", bold: true }, { text: "Multi-select from pre-built Fama-French factors plus any user-defined custom factors. Each factor shows a sparkline of historical returns. Weight sliders (sum to 100%) or equal-weight toggle." }]),
        bulletRuns([{ text: "Universe Configuration: ", bold: true }, { text: "Dropdown for index universe (S&P 500, Russell 1000, Russell 3000). Date range picker. Rebalance frequency selector. Transaction cost input." }]),
        bulletRuns([{ text: "Equity Curve Chart: ", bold: true }, { text: "Canvas-based line chart (reuse RRG chart pattern) showing strategy vs benchmark cumulative returns. Drawdown chart below. Hover shows exact date/value." }]),
        bulletRuns([{ text: "Statistics Panel: ", bold: true }, { text: "Compact grid of all metrics from the table above. Color-coded: green if Sharpe > 1, yellow if 0.5-1, red if < 0.5." }]),
        bulletRuns([{ text: "Factor Exposure Chart: ", bold: true }, { text: "Stacked area chart showing rolling factor betas over time. Helps users see when their strategy is actually just levered beta vs genuine alpha." }]),
        bulletRuns([{ text: "Pre/Post-Publication Split: ", bold: true }, { text: "Visual indicator showing performance before and after factor publication date, with a warning label explaining expected ~50% decay per the Dec 2025 paper." }]),

        // ══════════════════════════════════════════════════════════
        // PHASE 2: EVENT SCANNER
        // ══════════════════════════════════════════════════════════
        new Paragraph({ children: [new PageBreak()] }),
        heading("Phase 2: Event Scanner"),
        bodyRuns([
          { text: "The Event Scanner surfaces actionable corporate events in near-real-time, classified by type and ranked by historical alpha generation potential. Academic research shows alpha concentrates in the first month post-information release (9.84% annualized in month one, declining to 4.69% over months 1-4, then 1.99% thereafter), so speed and signal half-life tracking are critical." },
        ]),

        heading("2.1 Scientific Foundation", HeadingLevel.HEADING_2),
        body("The research report identifies five event categories with documented alpha, each with distinct signal characteristics:"),
        spacer(40),
        makeTable(
          ["Event Type", "Data Source", "Average Alpha", "Signal Half-Life", "Key Insight"],
          [
            ["Activist Positions (13D)", "SEC EDGAR", "6.33% announcement return", "5-10 day filing window", "Treatment effect 75.2%, stock picking 12.2%, selection bias 12.6%. 2024 SEC rule reduced filing window from 10 to 5 days."],
            ["Insider Trading Clusters", "SEC Form 4 (EDGAR)", "4.2 cents/share on purchases", "12+ months for top decile", "Purchases are consistently predictive; sales are mixed. Cluster detection (3+ insiders within 30 days) strengthens signal."],
            ["Unusual Options Activity", "Options flow APIs", "Statistically significant abnormal returns", "Days to weeks pre-event", "Predictive when options are: (a) large volume, (b) close to expiration, (c) out-of-the-money. O/S ratio predicts lower absolute CARs around earnings."],
            ["Earnings Surprises", "Earnings calendars + estimates", "~7.9% L/S spread over 60 days", "60+ days (PEAD)", "Bernard & Thomas (1989). Declining but still exploitable, especially for negative surprises."],
            ["8-K Material Events", "SEC EDGAR XBRL", "Varies by item type", "Days to weeks", "Key items: bankruptcy, receivership, termination of agreements, Reg FD disclosure, management changes."],
          ],
          [1600, 1300, 1600, 1400, 3460]
        ),

        heading("2.2 Backend Architecture", HeadingLevel.HEADING_2),
        heading("Complex Event Processing (CEP)", HeadingLevel.HEADING_3),
        body("The research report recommends a three-layer CEP architecture. Our implementation adapts this for a single-server FastAPI deployment:"),
        spacer(40),
        numberedRuns([{ text: "Event Producers: ", bold: true }, { text: "Scheduled background tasks (APScheduler or Celery Beat) polling data sources at defined intervals. EDGAR XBRL RSS feed (every 10 minutes for new filings), news API polling (every 5 minutes), options flow API (every 15 minutes during market hours)." }], "numbers3"),
        numberedRuns([{ text: "Processing Engine: ", bold: true }, { text: "Pattern matching, filtering, and aggregation layer. Deduplicate events across sources. Classify events into the five categories. Score events by historical alpha potential. Detect clusters (e.g., 3+ insider purchases within 30 days for the same ticker)." }], "numbers3"),
        numberedRuns([{ text: "Event Consumers: ", bold: true }, { text: "Dashboard updates (WebSocket push to frontend), alert triggers (stored in DB for user-defined rules), and integration with the Factor Backtester (events as tradeable signals)." }], "numbers3"),

        heading("Data Models", HeadingLevel.HEADING_3),
        bodyRuns([
          { text: "New SQLModel tables: " },
          { text: "Event", bold: true },
          { text: " (id, ticker, event_type, event_date, detection_timestamp, source, raw_data_json, alpha_estimate, signal_half_life, confidence_score), " },
          { text: "EventAlert", bold: true },
          { text: " (id, event_id, user_rule_id, triggered_at, acknowledged), " },
          { text: "AlertRule", bold: true },
          { text: " (id, name, event_types, tickers_filter, min_confidence, is_active)." },
        ]),

        heading("EDGAR Integration", HeadingLevel.HEADING_3),
        body("The research cites EDGAR-CORPUS (Loukas et al. 2021) and OpenEDGAR (arXiv 2018) as infrastructure references. Our implementation:"),
        bullet("Poll EDGAR XBRL RSS feed for new filings. Parse Schedule 13D (activist positions), Form 4 (insider trades), and 8-K (material events) filings."),
        bullet("For 13D filings: extract filer name, shares acquired, percentage ownership, and stated purpose. Flag when a known activist fund appears."),
        bullet("For Form 4 filings: extract transaction type (purchase/sale/exercise), shares, price, and insider role. Aggregate into cluster signals when multiple insiders trade within a rolling 30-day window."),
        bullet("For 8-K filings: parse item numbers to classify event type. Priority items: 1.02 (termination of agreement), 1.03 (bankruptcy), 2.01 (acquisition/disposition), 5.02 (management changes), 7.01 (Reg FD disclosure)."),

        heading("2.3 API Endpoints", HeadingLevel.HEADING_2),
        makeTable(
          ["Method", "Endpoint", "Description"],
          [
            ["GET", "/api/events/feed", "Real-time event feed with filters (event_type, ticker, min_confidence, date_range). Supports WebSocket upgrade for live streaming."],
            ["GET", "/api/events/{id}", "Full event detail including raw filing data, alpha estimate, and related events"],
            ["GET", "/api/events/ticker/{ticker}", "All events for a specific ticker, ordered by date"],
            ["POST", "/api/events/alerts/rules", "Create alert rule (event types, ticker filters, confidence threshold)"],
            ["GET", "/api/events/alerts", "List triggered alerts for the user"],
            ["GET", "/api/events/stats", "Aggregate statistics: events by type, average alpha by category, most active tickers"],
          ],
          [1000, 3200, 5160]
        ),

        heading("2.4 Frontend Components", HeadingLevel.HEADING_2),
        bodyRuns([
          { text: "The Event Scanner can either be a new standalone page (" },
          { text: "/events", bold: true },
          { text: ") or integrated as a panel within the Morning Brief page. Recommendation: standalone page with a notification badge in TopNav showing unread event count." },
        ]),
        spacer(40),
        bulletRuns([{ text: "Event Feed (main area): ", bold: true }, { text: "Chronological list of events, each showing: ticker, event type badge (color-coded), timestamp, headline summary, confidence score, estimated alpha, and signal age indicator (green if fresh, yellow if aging, red if past half-life)." }]),
        bulletRuns([{ text: "Filter Bar: ", bold: true }, { text: "Multi-select for event types (13D, Form 4, 8-K, Options, Earnings). Ticker search filter. Confidence threshold slider. Date range picker." }]),
        bulletRuns([{ text: "Event Detail Drawer: ", bold: true }, { text: "Click an event to expand a right-side drawer showing full filing text, historical alpha for this event type, related events for the same ticker, and a mini price chart showing the stock reaction." }]),
        bulletRuns([{ text: "Alert Configuration: ", bold: true }, { text: "Settings panel to create rules: select event types, optional ticker filter, minimum confidence, and notification preferences." }]),
        bulletRuns([{ text: "Alpha Decay Indicator: ", bold: true }, { text: "Every event shows a countdown-style indicator: days since event / expected half-life. When signal age exceeds half-life, visually mark the event as aged with reduced prominence." }]),

        // ══════════════════════════════════════════════════════════
        // PHASE 3: EARNINGS SURPRISE PREDICTOR
        // ══════════════════════════════════════════════════════════
        new Paragraph({ children: [new PageBreak()] }),
        heading("Phase 3: Earnings Surprise Predictor"),
        bodyRuns([
          { text: "The Earnings Surprise Predictor implements a SmartEstimate methodology inspired by LSEG StarMine, which achieves 70% directional accuracy on earnings surprise prediction when the SmartEstimate diverges from consensus by 2% or more. The alpha source is Post-Earnings Announcement Drift (PEAD), one of the most documented anomalies in finance: stock prices systematically drift in the direction of earnings surprises for 60+ days post-announcement." },
        ]),

        heading("3.1 Scientific Foundation", HeadingLevel.HEADING_2),
        heading("The SmartEstimate Methodology", HeadingLevel.HEADING_3),
        body("The core insight (SSRN 2007 paper on weighting individual analyst forecasts) is that equal-weighting all analysts is suboptimal. A weighted consensus that accounts for three dimensions reduces mean squared error by 3-15%:"),
        spacer(40),
        numberedRuns([{ text: "Recency: ", bold: true }, { text: "Apply exponential decay based on days since estimate. Stale estimates (>90 days) are excluded entirely. Recent estimates from the same analyst supersede older ones. The decay function: weight_recency = exp(-lambda * days_since_estimate), where lambda is calibrated so that a 90-day-old estimate has ~5% of the weight of a fresh estimate." }], "numbers4"),
        numberedRuns([{ text: "Analyst Accuracy: ", bold: true }, { text: "Track each analyst's rolling 8-quarter hit rate on direction AND magnitude of earnings surprises. Classify analysts into High-Quality (HQ) and Low-Quality (LQ) tiers. The market systematically overweighs LQ analysts, so isolating HQ signals extracts alpha. The HQ group's accuracy exceeds consensus accuracy 30 days before the announcement." }], "numbers4"),
        numberedRuns([{ text: "Broker Size: ", bold: true }, { text: "Use broker size (number of analysts employed) as a proxy for research resources. Larger brokers tend to have more comprehensive models, though this effect is weaker than recency and accuracy." }], "numbers4"),

        heading("The Predicted Surprise Formula", HeadingLevel.HEADING_3),
        body("Predicted Surprise = (SmartEstimate - Consensus Mean) / |Consensus Mean| x 100"),
        spacer(40),
        bodyRuns([
          { text: "A threshold of " },
          { text: "|Predicted Surprise| >= 2%", bold: true },
          { text: " triggers a signal. When both EPS and revenue SmartEstimates signal a surprise, cumulative track record shows 78% accuracy, with 86% on positive calls and 67.5% on negative calls (StarMine 2011 Q4-2025 Q2 data for S&P 500)." },
        ]),

        heading("PEAD as the Alpha Source", HeadingLevel.HEADING_3),
        body("Bernard and Thomas (1989) established that stock prices systematically drift in the direction of earnings surprises for 60+ days. A hedge strategy going long the highest surprise decile and short the lowest generates approximately 7.9% excess return in 60 days. While PEAD has declined due to increased arbitrage activity, it remains exploitable, particularly for negative surprises where analyst optimism bias creates persistent underreaction."),

        heading("3.2 Backend Architecture", HeadingLevel.HEADING_2),
        heading("Estimate Data Pipeline", HeadingLevel.HEADING_3),
        bodyRuns([
          { text: "New service: " },
          { text: "backend/services/earnings_engine.py", bold: true },
        ]),
        bullet("Data ingestion: pull individual analyst estimates from financial data API (FMP, Alpha Vantage, or Zacks). Store each estimate with: analyst_id, broker, ticker, metric (EPS/Revenue), period (Q1/Q2/annual), estimate_value, estimate_date, ingestion_timestamp."),
        bullet("Staleness filter: exclude any estimate older than 90 days from the calculation. Apply Bloomberg-style outlier detection to flag and exclude sign errors and magnitude errors (e.g., an estimate that is 10x the consensus mean)."),
        bullet("Analyst scoring: maintain a rolling accuracy table. For each analyst-ticker pair, track the last 8 quarters of actual vs estimated EPS. Compute directional hit rate (did they predict the surprise direction correctly?) and magnitude accuracy (MAPE). Classify into HQ/LQ tiers based on a threshold (e.g., top quartile = HQ)."),
        bullet("SmartEstimate computation: for each ticker approaching earnings, compute the weighted average using the three-dimensional weighting scheme. Cache the result with TTL matching the recomputation schedule (daily during earnings season, weekly otherwise)."),

        heading("Data Models", HeadingLevel.HEADING_3),
        bodyRuns([
          { text: "New tables: " },
          { text: "AnalystEstimate", bold: true },
          { text: " (id, analyst_id, broker, ticker, metric, period, value, estimate_date, ingestion_ts), " },
          { text: "AnalystScore", bold: true },
          { text: " (analyst_id, ticker, hit_rate_8q, mape_8q, tier, last_updated), " },
          { text: "SmartEstimate", bold: true },
          { text: " (ticker, metric, period, smart_value, consensus_value, predicted_surprise_pct, signal_direction, confidence, computed_at), " },
          { text: "EarningsSurpriseHistory", bold: true },
          { text: " (ticker, period, actual, consensus_at_report, smart_at_report, surprise_pct, report_date)." },
        ]),

        heading("3.3 API Endpoints", HeadingLevel.HEADING_2),
        makeTable(
          ["Method", "Endpoint", "Description"],
          [
            ["GET", "/api/earnings/calendar", "Upcoming earnings dates with SmartEstimate signals for watchlist and universe"],
            ["GET", "/api/earnings/surprise/{ticker}", "Current SmartEstimate, consensus, predicted surprise, confidence, and analyst breakdown for a specific ticker"],
            ["GET", "/api/earnings/history/{ticker}", "Historical earnings surprises with SmartEstimate accuracy tracking"],
            ["GET", "/api/earnings/signals", "All active predicted surprise signals (|PS| >= 2%) ranked by confidence"],
            ["GET", "/api/earnings/analyst/{analyst_id}", "Analyst scorecard: accuracy tier, hit rate, covered tickers, track record"],
            ["GET", "/api/earnings/leaderboard", "Top analysts by accuracy for a given sector or universe"],
          ],
          [1000, 3400, 4960]
        ),

        heading("3.4 Frontend Components", HeadingLevel.HEADING_2),
        bodyRuns([
          { text: "Integration point: this feature enhances the existing " },
          { text: "Screener", bold: true },
          { text: " and " },
          { text: "Morning Brief", bold: true },
          { text: " pages rather than creating a wholly new page. The primary UI surface is an " },
          { text: "Earnings tab within the Screener", bold: true },
          { text: " and a " },
          { text: "Surprise Signals panel on Morning Brief", bold: true },
          { text: "." },
        ]),
        spacer(40),
        bulletRuns([{ text: "Earnings Calendar View: ", bold: true }, { text: "Week-view calendar showing upcoming earnings dates. Each entry shows: ticker, reporting time (BMO/AMC), SmartEstimate vs consensus, predicted surprise %, and a colored confidence indicator (high/medium/low)." }]),
        bulletRuns([{ text: "Surprise Signal Cards: ", bold: true }, { text: "On Morning Brief, show the top 5-10 highest-confidence predicted surprise signals for the upcoming week. Each card: ticker, direction (beat/miss), magnitude, analyst consensus breakdown, and PEAD historical performance for that surprise magnitude." }]),
        bulletRuns([{ text: "Analyst Weighting Visualization: ", bold: true }, { text: "When viewing a specific ticker's SmartEstimate, show a breakdown chart: each analyst as a horizontal bar, length = weight in the SmartEstimate, color = accuracy tier (HQ green, LQ gray), label = broker name and estimate value." }]),
        bulletRuns([{ text: "Historical Accuracy Tracker: ", bold: true }, { text: "Running tally of AlphaDesk SmartEstimate accuracy vs simple consensus, displayed as a scoreboard. This builds user trust and validates the methodology over time." }]),

        // ══════════════════════════════════════════════════════════
        // PHASE 4: NEWS SENTIMENT SCORING
        // ══════════════════════════════════════════════════════════
        new Paragraph({ children: [new PageBreak()] }),
        heading("Phase 4: News Sentiment Scoring"),
        bodyRuns([
          { text: "News Sentiment Scoring applies NLP models to financial news to generate per-ticker sentiment scores, track sentiment velocity (rate of change), and detect contrarian divergences between sentiment and price action. The research report emphasizes that proper temporal isolation is essential, as previous studies grossly overstated news impact due to data contamination." },
        ]),

        heading("4.1 Scientific Foundation", HeadingLevel.HEADING_2),
        heading("FinBERT: The State of the Art", HeadingLevel.HEADING_3),
        body("FinBERT (Araci 2019) is a BERT-based model fine-tuned on financial corpora that substantially outperforms general-purpose sentiment tools and traditional ML methods (naive Bayes, SVM, random forest, CNN, LSTM) in financial sentiment classification. It excels at identifying contextual sentiment in financial text where general-purpose dictionaries fail (e.g., the word \"liability\" is negative in general English but neutral in financial context)."),

        heading("Loughran-McDonald Dictionary", HeadingLevel.HEADING_3),
        body("The Loughran-McDonald Master Dictionary (Notre Dame SRAF) provides seven sentiment categories with word lists specifically calibrated for financial text: negative (2,329 words), positive (354 words), uncertainty, litigious, strong modal, weak modal, and constraining. The research report notes that nearly three-fourths of words classified as negative by general-purpose dictionaries (e.g., General Inquirer) are not negative in financial context, validating the need for domain-specific lexicons."),

        heading("Contrarian Signals", HeadingLevel.HEADING_3),
        bodyRuns([
          { text: "A Stanford NLP study (CS224N) achieves 54.4% mean directional accuracy on stock return predictions using news-based models with proper look-ahead bias controls. The critical finding: previous studies grossly overstated accuracy due to data contamination. For contrarian signal detection, the pipeline tracks " },
          { text: "sentiment velocity", bold: true },
          { text: " (rate of change in aggregate sentiment) and flags divergences from price action. When sentiment reaches extreme negative readings while price stabilizes, this historically signals mean reversion opportunities." },
        ]),

        heading("4.2 Backend Architecture", HeadingLevel.HEADING_2),
        heading("Sentiment Pipeline", HeadingLevel.HEADING_3),
        bodyRuns([
          { text: "New service: " },
          { text: "backend/services/sentiment_engine.py", bold: true },
          { text: ". Five-stage pipeline as specified in the research report:" },
        ]),
        spacer(40),
        numberedRuns([{ text: "Ingestion: ", bold: true }, { text: "Poll news API (NewsAPI, Finnhub, or Benzinga) for headlines and article summaries. Store raw articles with: source, headline, body_snippet, published_at, tickers_mentioned. Deduplicate across sources using headline similarity hashing." }]),
        numberedRuns([{ text: "Scoring: ", bold: true }, { text: "Run each headline through FinBERT for a -1 to +1 sentiment score. Extend with Loughran-McDonald word counts for granular category scores (uncertainty, litigious, constraining). Store both the FinBERT score and the L-M category breakdown per article." }]),
        numberedRuns([{ text: "Aggregation: ", bold: true }, { text: "Compute rolling sentiment scores per ticker using exponentially weighted windows: 24-hour (intraday signal), 7-day (weekly trend), and 30-day (monthly baseline). Weight more recent articles higher within each window." }]),
        numberedRuns([{ text: "Velocity: ", bold: true }, { text: "Compute first derivative of the sentiment time series. Flag accelerations (rapid sentiment improvement) and decelerations (rapid deterioration). Velocity spikes often precede price moves." }]),
        numberedRuns([{ text: "Divergence: ", bold: true }, { text: "Correlate sentiment velocity with price returns over matching windows. Generate contrarian alerts when the correlation breaks down: extreme negative sentiment + stable/rising price = potential long opportunity, extreme positive sentiment + declining price = potential risk." }]),

        heading("Model Deployment", HeadingLevel.HEADING_3),
        body("FinBERT will run as a local Python model (ProsusAI/finbert from HuggingFace, ~440MB). For the initial deployment, we can use our existing OpenRouter integration to score sentiment via LLM if GPU resources are limited, with a structured prompt that mimics FinBERT's three-class output (positive/negative/neutral with confidence). This gives us a working pipeline immediately while we optimize for local model inference later."),

        heading("Data Models", HeadingLevel.HEADING_3),
        bodyRuns([
          { text: "New tables: " },
          { text: "NewsArticle", bold: true },
          { text: " (id, source, headline, body_snippet, published_at, url, tickers_json, ingestion_ts), " },
          { text: "SentimentScore", bold: true },
          { text: " (article_id, ticker, finbert_score, finbert_confidence, lm_negative, lm_positive, lm_uncertainty, lm_litigious), " },
          { text: "TickerSentiment", bold: true },
          { text: " (ticker, window, score, velocity, article_count, computed_at), " },
          { text: "SentimentAlert", bold: true },
          { text: " (ticker, alert_type, sentiment_score, price_return, divergence_magnitude, created_at)." },
        ]),

        heading("4.3 API Endpoints", HeadingLevel.HEADING_2),
        makeTable(
          ["Method", "Endpoint", "Description"],
          [
            ["GET", "/api/sentiment/{ticker}", "Current sentiment scores (24h/7d/30d), velocity, and L-M category breakdown"],
            ["GET", "/api/sentiment/{ticker}/history", "Historical sentiment time series for charting"],
            ["GET", "/api/sentiment/alerts", "Active contrarian divergence alerts, ranked by divergence magnitude"],
            ["GET", "/api/sentiment/movers", "Tickers with largest sentiment velocity changes (biggest sentiment shifts today)"],
            ["GET", "/api/sentiment/news/{ticker}", "Recent news articles for a ticker with individual sentiment scores"],
            ["GET", "/api/sentiment/heatmap", "Sector-level sentiment aggregation for market-wide view"],
          ],
          [1000, 3400, 4960]
        ),

        heading("4.4 Frontend Components", HeadingLevel.HEADING_2),
        bodyRuns([
          { text: "Sentiment integrates across multiple existing pages rather than being a standalone view:" },
        ]),
        spacer(40),
        bulletRuns([{ text: "Morning Brief - Sentiment Movers Panel: ", bold: true }, { text: "Replaces or augments the existing Market Drivers panel. Shows top 5 tickers by sentiment velocity change today, with sparkline of 7-day sentiment trend and price overlay." }]),
        bulletRuns([{ text: "Screener - Sentiment Column: ", bold: true }, { text: "Add sentiment score and velocity as sortable columns in the screener results table. Color-coded: green (positive momentum), red (negative), yellow (extreme = contrarian opportunity)." }]),
        bulletRuns([{ text: "Stock Detail - Sentiment Chart: ", bold: true }, { text: "When viewing a stock in the Screener detail view, show a dual-axis chart: price (left axis) and sentiment score (right axis) over time. Highlight divergence periods with a shaded background." }]),
        bulletRuns([{ text: "Contrarian Alert Badge: ", bold: true }, { text: "In the TopNav, show a small badge count of active contrarian divergence alerts. Clicking opens a dropdown with the alert details." }]),

        // ══════════════════════════════════════════════════════════
        // INTEGRATION & SHARED INFRASTRUCTURE
        // ══════════════════════════════════════════════════════════
        new Paragraph({ children: [new PageBreak()] }),
        heading("Shared Infrastructure and Integration"),

        heading("How the Features Connect", HeadingLevel.HEADING_2),
        body("The four features are designed to reinforce each other through a shared data layer and cross-feature signal integration:"),
        spacer(40),
        bulletRuns([{ text: "Factor Backtester + Earnings Surprise: ", bold: true }, { text: "Earnings surprise signals become testable factors. Users can backtest a strategy that goes long predicted positive surprises and short predicted negatives, measuring whether the SmartEstimate adds alpha beyond simple consensus." }]),
        bulletRuns([{ text: "Event Scanner + Factor Backtester: ", bold: true }, { text: "Events (13D filings, insider clusters) become event-driven factors. Backtest the alpha decay profile of each event type against the documented half-lives." }]),
        bulletRuns([{ text: "News Sentiment + Earnings Surprise: ", bold: true }, { text: "Pre-earnings sentiment provides a complementary signal. If the SmartEstimate predicts a positive surprise AND sentiment is already euphoric, the PEAD opportunity may be reduced (priced in). If SmartEstimate predicts positive but sentiment is negative, the surprise effect may be amplified." }]),
        bulletRuns([{ text: "News Sentiment + Event Scanner: ", bold: true }, { text: "Sentiment velocity spikes can serve as early warning signals for upcoming events. A sudden sentiment deterioration may precede an 8-K filing." }]),
        bulletRuns([{ text: "All Features + Screener: ", bold: true }, { text: "Every signal (factor scores, events, predicted surprises, sentiment) becomes a filterable and sortable column in the Stock Screener. Users can compose multi-signal screens: e.g., 'Show me stocks with predicted positive earnings surprise > 5% AND recent insider buying clusters AND improving sentiment velocity.'" }]),

        heading("Existing Codebase Integration Points", HeadingLevel.HEADING_2),
        body("The current backend architecture (FastAPI + SQLModel + yfinance + OpenRouter) provides natural extension points:"),
        spacer(40),
        makeTable(
          ["Existing Component", "Integration", "Changes Required"],
          [
            ["yfinance_service.py", "Already provides price history, fundamentals, and macro data. Factor engine and earnings engine both consume this.", "Add new methods for earnings calendar and analyst estimate data. Consider caching layer upgrade (Redis vs current lru_cache)."],
            ["claude_service.py (OpenRouter)", "Sentiment scoring can use LLM as a fallback when FinBERT is unavailable. Stock grader prompts can incorporate earnings surprise and sentiment data.", "Add sentiment scoring prompt template. Extend stock grader prompt to include SmartEstimate divergence and event context."],
            ["portfolio_math.py", "Factor backtester shares optimization code (scipy minimize). Portfolio risk decomposition benefits from factor exposure data.", "Extract shared optimization utilities. Add factor regression methods."],
            ["database.py (SQLModel + SQLite)", "All new features add tables to the same database. PiT enforcement adds timestamp columns.", "Consider PostgreSQL migration for concurrent writes during event ingestion. Add migration tooling (Alembic)."],
            ["weight_calculator.py", "Regime detection already influences stock grading. Extend to adjust factor weights and sentiment thresholds by regime.", "Add regime-aware factor weight adjustments. Flag when current regime reduces expected alpha for a factor."],
            ["Frontend: TopNav, Screener, MorningBrief", "New pages (Backtester, Events) add to TopNav. Earnings and sentiment integrate into existing Screener and MorningBrief.", "Add routes. Extend Screener results columns. Add MorningBrief panels."],
          ],
          [2000, 3500, 3860]
        ),

        // ══════════════════════════════════════════════════════════
        // ALPHA DECAY & SIGNAL MANAGEMENT
        // ══════════════════════════════════════════════════════════
        new Paragraph({ children: [new PageBreak()] }),
        heading("Alpha Decay and Signal Management"),
        bodyRuns([
          { text: "The research report emphasizes a universal pattern: " },
          { text: "alpha concentrates in the first month post-information release and decays rapidly.", bold: true },
          { text: " Institutional alpha on new trades declines over 12 months, with competition driving more aggressive early trading. Factor alpha decays ~50% post-publication. Every feature in AlphaDesk must account for this reality." },
        ]),
        spacer(80),
        heading("Signal Half-Life Framework", HeadingLevel.HEADING_2),
        body("Each signal type gets a documented half-life based on academic evidence. The system tracks signal age and alerts users when signals are aging beyond their predictive window:"),
        spacer(40),
        makeTable(
          ["Signal Type", "Expected Half-Life", "Academic Source", "UI Treatment"],
          [
            ["13D Activist Filing", "5-10 days", "2024 SEC rule change; Brav et al.", "Red warning after 10 days"],
            ["Insider Cluster", "3-6 months", "Lei (UMich) top decile analysis", "Yellow after 3 months, red after 6"],
            ["Unusual Options Activity", "Days to 2 weeks", "Wayne State JPM 2026 paper", "Red warning after 14 days"],
            ["Earnings Surprise (PEAD)", "60+ days", "Bernard & Thomas (1989)", "Yellow after 30 days, red after 60"],
            ["Predicted Surprise (pre-earnings)", "Until earnings date", "StarMine methodology", "Expires on report date"],
            ["Sentiment Divergence", "1-4 weeks", "Stanford CS224N study", "Yellow after 2 weeks, red after 4"],
            ["Factor Signal", "~50% of backtest", "Dec 2025 alpha decay paper", "Show pre/post-publication split"],
          ],
          [2200, 1600, 2800, 2760]
        ),

        heading("Key Academic References", HeadingLevel.HEADING_2),
        body("The full bibliography is maintained in the attached research PDF. The most critical papers for implementation:"),
        spacer(40),
        bulletRuns([{ text: "Analyst Weighting: ", bold: true }, { text: "\"On the Weighting of Individual Analyst Forecasts in the Consensus\" (SSRN, 2007) - foundation for SmartEstimate methodology" }]),
        bulletRuns([{ text: "PEAD: ", bold: true }, { text: "Bernard & Thomas (1989) \"Post-Earnings Announcement Drift\" - foundation for earnings surprise alpha" }]),
        bulletRuns([{ text: "Event Detection: ", bold: true }, { text: "Lu et al. (ACL 2021) \"Trade the Event\" - bi-level event detection from news articles" }]),
        bulletRuns([{ text: "Factor Models: ", bold: true }, { text: "Fama & French (1993, 2015) three-factor and five-factor models" }]),
        bulletRuns([{ text: "Look-Ahead Bias: ", bold: true }, { text: "\"Look-Ahead-Bench\" (arXiv, Jan 2026) - demonstrates LLM look-ahead bias in financial workflows" }]),
        bulletRuns([{ text: "Alpha Decay: ", bold: true }, { text: "\"Not All Factors Crowd Equally\" (arXiv, Dec 2025) - game-theoretic model of post-publication factor decay" }]),
        bulletRuns([{ text: "Financial NLP: ", bold: true }, { text: "Araci (2019) \"FinBERT: Financial Sentiment Analysis with Pre-trained Language Models\"" }]),
        bulletRuns([{ text: "Financial Lexicon: ", bold: true }, { text: "Loughran-McDonald Master Dictionary (Notre Dame SRAF) - domain-specific sentiment word lists" }]),
        bulletRuns([{ text: "Survivorship Bias: ", bold: true }, { text: "Quantified Strategies analysis showing 4x return inflation from excluding delistings" }]),
        bulletRuns([{ text: "Covariance Estimation: ", bold: true }, { text: "Ledoit & Wolf (2004) \"Improved Estimation of the Covariance Matrix\" for portfolio risk" }]),
      ]
    },
  ]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/sessions/sleepy-charming-ramanujan/mnt/alpha-desk/ROADMAP_V2.docx", buffer);
  console.log("Document created successfully");
});
