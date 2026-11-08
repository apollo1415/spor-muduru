#!/usr/bin/env python3
"""Discover broad provider fixture coverage without approving fixture or odds joins."""
import argparse
import csv
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from zoneinfo import ZoneInfo

from odds_ev import utc_date

IST = ZoneInfo("Europe/Istanbul")
COLUMNS = ["event_id", "provider_sport", "provider_home", "provider_away",
           "provider_kickoff_utc", "league", "home", "away", "kickoff_istanbul",
           "home_similarity", "away_similarity", "kickoff_delta_minutes", "status"]
INVENTORY_COLUMNS = ["event_id", "provider_sport", "home", "away",
                     "kickoff_utc", "kickoff_istanbul", "status",
                     "official_fixture_verified", "real_odds_verified", "ev_verified"]


def score(a, b):
    return SequenceMatcher(None, a.casefold().strip(), b.casefold().strip()).ratio()


def candidates(matches, events, sport, minimum=.65, max_minutes=30):
    found = []
    for event in events:
        try:
            kickoff = utc_date(event["commence_time"])
            for match in matches:
                if match.get("decision") != "MODEL_ONLY_NO_ODDS":
                    continue
                match_time = utc_date(match["kickoff_istanbul"])
                delta = abs((kickoff - match_time).total_seconds()) / 60
                if delta > max_minutes:
                    continue
                home_score = score(event["home_team"], match["home"])
                away_score = score(event["away_team"], match["away"])
                if home_score < minimum or away_score < minimum:
                    continue
                found.append({
                    "event_id": event["id"], "provider_sport": sport,
                    "provider_home": event["home_team"], "provider_away": event["away_team"],
                    "provider_kickoff_utc": event["commence_time"], "league": match["league"],
                    "home": match["home"], "away": match["away"],
                    "kickoff_istanbul": match["kickoff_istanbul"],
                    "home_similarity": round(home_score, 3), "away_similarity": round(away_score, 3),
                    "kickoff_delta_minutes": round(delta, 2),
                    "status": "REVIEW_REQUIRED_NOT_APPROVED",
                })
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(found, key=lambda row: (row["event_id"], -min(row["home_similarity"], row["away_similarity"])))


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "spor-muduru-discovery/0.2"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def soccer_sports(sports):
    """Return active soccer keys advertised by the provider."""
    return sorted({item["key"] for item in sports
                   if item.get("active", True)
                   and str(item.get("group", "")).casefold() == "soccer"
                   and item.get("key")})


def provider_sports(api_key, requested=None, loader=fetch_json):
    """Use an explicit override or discover all currently active soccer competitions."""
    if requested:
        return list(dict.fromkeys(value.strip() for value in requested.split(",") if value.strip())), "EXPLICIT"
    query = urllib.parse.urlencode({"apiKey": api_key})
    sports = loader("https://api.the-odds-api.com/v4/sports/?" + query)
    return soccer_sports(sports), "PROVIDER_ACTIVE_SOCCER"


def event_url(sport, api_key, start, end):
    params = urllib.parse.urlencode({
        "apiKey": api_key,
        "dateFormat": "iso",
        "commenceTimeFrom": start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "commenceTimeTo": end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    return "https://api.the-odds-api.com/v4/sports/" + urllib.parse.quote(sport, safe="") + "/events?" + params


def daily_inventory(events, day):
    """Expose provider-only daily fixtures separately and keep every validation flag false."""
    rows = []
    seen = set()
    for event in events:
        try:
            event_id = event["id"]
            if event_id in seen:
                continue
            kickoff = utc_date(event["commence_time"])
            local = kickoff.astimezone(IST)
            if local.date().isoformat() != day:
                continue
            seen.add(event_id)
            rows.append({
                "event_id": event_id,
                "provider_sport": event.get("sport_key", ""),
                "home": event["home_team"],
                "away": event["away_team"],
                "kickoff_utc": kickoff.isoformat(),
                "kickoff_istanbul": local.isoformat(),
                "status": "UNVERIFIED_PROVIDER_FIXTURE",
                "official_fixture_verified": "NO",
                "real_odds_verified": "NO",
                "ev_verified": "NO",
            })
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(rows, key=lambda row: (row["kickoff_istanbul"], row["provider_sport"], row["home"], row["away"]))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matches", default="reports/today/matches.csv")
    parser.add_argument("--out", default="reports/odds")
    parser.add_argument("--daily-out", default="reports/today")
    parser.add_argument("--date", default=datetime.now(IST).date().isoformat())
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--sports", default=None,
                        help="Optional comma-separated override. Default: all active provider soccer competitions.")
    args = parser.parse_args()
    if not 1 <= args.days <= 30:
        raise SystemExit("days must be 1..30")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(args.matches, encoding="utf-8-sig", newline="") as handle:
        matches = list(csv.DictReader(handle))

    key = os.environ.get("ODDS_API_KEY")
    requested = args.sports or os.environ.get("ODDS_SPORTS")
    results = []
    statuses = []
    all_events = []
    selection = "NO_API_KEY"
    sports = []
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)
    end = now + timedelta(days=args.days)
    if key:
        try:
            sports, selection = provider_sports(key, requested=requested)
        except Exception:
            selection = "SPORT_LIST_FETCH_FAILED"
        for sport in sports:
            try:
                events = fetch_json(event_url(sport, key, start, end))
                normalized = [{**event, "sport_key": event.get("sport_key") or sport} for event in events]
                results.extend(candidates(matches, normalized, sport))
                all_events.extend(normalized)
                statuses.append({"sport": sport, "status": "EVENTS_FETCHED", "events": len(normalized)})
            except Exception:
                # Do not expose exception text: HTTP errors can include a secret-bearing URL.
                statuses.append({"sport": sport, "status": "FETCH_FAILED", "events": 0})

    daily_rows = daily_inventory(all_events, args.date)
    (out / "provider_events.json").write_text(json.dumps(all_events, ensure_ascii=False), encoding="utf-8")
    write_csv(out / "fixture_candidates.csv", COLUMNS, results)
    write_csv(Path(args.daily_out) / "provider_fixture_inventory.csv", INVENTORY_COLUMNS, daily_rows)
    summary = {
        "api_key_present": bool(key),
        "sport_selection": selection,
        "sports_attempted": len(sports),
        "provider_events": len(all_events),
        "provider_events_today": len(daily_rows),
        "candidates": len(results),
        "sports": statuses,
        "event_endpoint_includes_odds": False,
        "official_fixture_verified": False,
        "real_odds_verified": False,
        "ev_verified": False,
        "approval": "NONE",
        "warning": "Provider events broaden inventory only. They are not an official Iddaa coupon, approved fixture joins, verified odds or validated EV.",
    }
    (out / "discovery_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "sports"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
