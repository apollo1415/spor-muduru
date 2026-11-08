# SPOR MÜDÜRÜ v0.2
Personal non-commercial research prototype. Data attribution: https://github.com/oladeeayo/open-matchday

Run: `python spor_muduru.py --date 2026-11-07 --out reports/today`.

GitHub Actions: Actions → SPOR MUDURU daily free-data inventory → Run workflow. Scheduled 05:00 UTC (08:00 Türkiye); GitHub schedules may run late. Download artifact `spor-muduru-report` containing `matches.csv`, `coverage.csv`, `summary.json`.

**Important:** This is a baseline, not a finished betting prediction system. The source covers its listed competitions, not the entire official İddaa bulletin. It has no live bookmaker odds, no calibrated model, no injury/lineup feeds, no verified backtesting, and no automated bridge into ChatGPT scheduled tasks. Unknown data stays unknown. Source match dates and kickoff times need official cross-checks. Review data source licenses and terms before redistribution or commercial use.

## Walk-forward backtest (v0.4)

`python backtest.py --date 2026-11-07 --out reports/backtest`

Runs each historical league match against **only matches dated earlier**, with a minimum 30 league results and 5 matching home/away observations. Outputs `predictions.csv`, `league_metrics.csv`, `summary.json`; GitHub Actions publishes these as `spor-muduru-backtest`. Metrics: Brier score, log loss, observed frequency vs predicted mean and sample sufficiency flag (n>=30). Markets include 1X2, over 2.5, BTTS, corners, shots, shots on target, first-half goals and first-half corners when available. These are retrospective evaluations against potentially revised source data, not verified forward performance. No odds/ROI and no promise of profitability. Uncalibrated models remain exploratory.


## Full daily fixture research table (provenance first)

The daily workflow now publishes a separate artifact named
**spor-muduru-full-fixture-research** containing:

- \`all_visible_matches.csv\`: every date-matching fixture visible in the
  existing source/horizon inventory, plus the unverified provider inventory.
  Duplicates inside the source/horizon are removed only for exact
  league/home/away/kickoff identity. Provider rows remain **separate**
  until explicitly approved. The count is NOT a deduplicated official Iddaa
  coupon count.
- \`coverage_summary.json\`: explicit source/provider row totals, number of
  research model forecasts, missing 1X2 forecasts, and unavailable official
  coupon coverage percentage.

For an offline reproducible run after the daily pipeline has produced its
input CSV files:

\`\`\`bash
python full_fixture_report.py --date 2026-11-09 --out reports/full-fixture
python -m unittest test_full_fixture_report -v
\`\`\`

**Güven %** (last CSV column) means the model's probability of the most
likely 1-X-2 outcome **only when three coherent probabilities exist**. It is
not a backtested win rate, a calibrated confidence score, or a recommendation.
Every such research probability is labeled as an experimental team model,
a non-team-specific historical league prior, or an unapproved provider review.
No data means a blank, not an invented 33/33/33 split. Started matches have
no fresh pre-kickoff forecast. Unverified provider rows are not silently
promoted to official fixtures.

The source and provider inventories are **not** a verified complete official
İddaa bulletin. More complete official match feed access, independent kickoff
and identity reconciliation, model calibration, and live odds still require
separate work; GitHub Action success alone proves none of these.
