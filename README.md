# SPOR MÜDÜRÜ v0.2
Personal non-commercial research prototype. Data attribution: https://github.com/oladeeayo/open-matchday

Run: `python spor_muduru.py --date 2026-11-07 --out reports/today`.

GitHub Actions: Actions → SPOR MUDURU daily free-data inventory → Run workflow. Scheduled 05:00 UTC (08:00 Türkiye); GitHub schedules may run late. Download artifact `spor-muduru-report` containing `matches.csv`, `coverage.csv`, `summary.json`.

**Important:** This is a baseline, not a finished betting prediction system. The source covers its listed competitions, not the entire official İddaa bulletin. It has no live bookmaker odds, no calibrated model, no injury/lineup feeds, no verified backtesting, and no automated bridge into ChatGPT scheduled tasks. Unknown data stays unknown. Source match dates and kickoff times need official cross-checks. Review data source licenses and terms before redistribution or commercial use.
