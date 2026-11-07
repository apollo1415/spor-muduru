#!/usr/bin/env python3
"""Evaluate earliest archived pre-match predictions using prior Actions artifacts."""
import argparse
import io
import json
import os
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from prospective_evaluation import evaluate
from spor_muduru import csvrows

def github_json(url, token):
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "spor-muduru-prospective-research"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

def archive_predictions(repo, token, current_run, limit=30):
    url = f"https://api.github.com/repos/{repo}/actions/artifacts?per_page=100"
    artifacts = github_json(url, token).get("artifacts", [])
    artifacts = [a for a in artifacts if a.get("name") == "spor-muduru-forward-snapshot"
                 and not a.get("expired") and str(a.get("workflow_run", {}).get("id")) != str(current_run)]
    snapshots = []
    failures = []
    for artifact in artifacts[:limit]:
        request = urllib.request.Request(artifact["archive_download_url"], headers={
            "Authorization": "Bearer " + token, "User-Agent": "spor-muduru-prospective-research"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                archive = zipfile.ZipFile(io.BytesIO(response.read()))
            with archive:
                for name in archive.namelist():
                    if name.endswith(".json") and Path(name).name.startswith("predictions_"):
                        snapshots.append(json.loads(archive.read(name)))
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
            failures.append({"artifact_id": artifact.get("id"), "error_type": type(exc).__name__, "detail": str(exc)[:160]})
            continue
    return snapshots, len(artifacts), failures

def earliest_predictions(snapshots):
    first = {}
    for snapshot in snapshots:
        for row in snapshot.get("predictions", []):
            try:
                key = (row["league"], row["home"], row["away"], row["kickoff_istanbul"])
                stamp = datetime.fromisoformat(row["captured_at_utc"].replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    continue
                if key not in first or stamp < first[key][0]:
                    first[key] = (stamp, row)
            except (KeyError, TypeError, ValueError):
                continue
    return [item[1] for item in first.values()]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="reports/prospective/evaluation.json")
    p.add_argument("--limit", type=int, default=30)
    args = p.parse_args()
    token, repo = os.getenv("GH_TOKEN", ""), os.getenv("GITHUB_REPOSITORY", "")
    if not token or not repo:
        raise SystemExit("GH_TOKEN and GITHUB_REPOSITORY required")
    snapshots, available, download_failures = archive_predictions(repo, token, os.getenv("GITHUB_RUN_ID", ""), args.limit)
    forecasts = earliest_predictions(snapshots)
    leagues = sorted({r["league"] for r in forecasts})
    results, failures = [], []
    for league in leagues:
        try:
            results.extend(dict(r, league=league) for r in csvrows(f"data/{league}/results_2627.csv"))
        except Exception:
            failures.append(league)
    report = evaluate({"predictions": forecasts}, results, datetime.now(timezone.utc))
    report.update({"snapshots_read": len(snapshots), "snapshot_artifacts_available": available, "archive_download_failures": download_failures,
                   "unique_forecasts": len(forecasts), "result_source_failures": failures,
                   "note": "Only prior CI artifacts, earliest timestamp per fixture. Source results and fixture times not independently verified. Artifacts expire after 90 days."})
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"snapshots_read": len(snapshots), "snapshot_artifacts_available": available,
                      "archive_download_failures": download_failures, "unique_forecasts": len(forecasts),
                      "scored_matches": report["scored_matches"], "result_source_failures": failures,
                      "approved_for_betting": 0}))
    if available and not snapshots:
        raise SystemExit("FAIL: Prior snapshot artifacts exist but none could be read; inspect archive_download_failures")

if __name__ == "__main__":
    main()
