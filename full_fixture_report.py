#!/usr/bin/env python3
"""Daily all-visible-fixture research table, with provenance and no invented probabilities.

Provider events are deliberately not silently merged into source fixtures or the
official Iddaa bulletin. This is a coverage and model-availability artifact.
"""
import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Europe/Istanbul")
COLUMNS = [
    "Tarih", "Kaynak", "Kaynak ID", "Lig", "Saat (TSI)", "Ev sahibi",
    "Deplasman", "Resmi Iddaa", "Kimlik kontrolu", "Mac durumu",
    "Model turu", "Kalibrasyon", "Ev orneklem", "Deplasman orneklem",
    "MS 1 %", "MS X %", "MS 2 %", "2.5 Ust %", "KG Var %",
    "MS tahmini", "Diger pazarlar", "Aciklama", "Güven %",
]


def read_rows(path):
    if not path or not Path(path).is_file():
        return []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def local_kickoff(raw):
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt.astimezone(IST) if dt.tzinfo else None
    except ValueError:
        return None


def probability_triplet(row):
    try:
        values = [float(row[key]) for key in ("p_home", "p_draw", "p_away")]
    except (KeyError, TypeError, ValueError):
        return None
    if not all(math.isfinite(v) and 0 <= v <= 1 for v in values):
        return None
    if not 0.98 <= sum(values) <= 1.02:
        return None
    return values


def market_percent(raw):
    try:
        value = float(raw)
        return round(value * 100, 1) if math.isfinite(value) and 0 <= value <= 1 else ""
    except (TypeError, ValueError):
        return ""


def fixture_key(row):
    return (
        row.get("league", "").casefold().strip(),
        row.get("home", "").casefold().strip(),
        row.get("away", "").casefold().strip(),
        row.get("kickoff_istanbul", "").strip(),
    )


def make_row(f, day, now, origin, fallback=None, review=None):
    kick = local_kickoff(f.get("kickoff_istanbul"))
    if kick is not None and kick.date().isoformat() != day:
        return None
    if kick is None and f.get("source_date") != day:
        return None
    is_past = kick is not None and kick <= now
    status = ("BASLADI" if is_past else
              "SAAT_DOGRULANAMADI" if kick is None else "BASLAMADI")

    out = {field: "" for field in COLUMNS}
    out.update({
        "Tarih": day,
        "Kaynak": origin,
        "Kaynak ID": f.get("event_id", ""),
        "Lig": f.get("league", "") or f.get("provider_sport", ""),
        "Saat (TSI)": kick.strftime("%H:%M") if kick else "",
        "Ev sahibi": f.get("home", ""),
        "Deplasman": f.get("away", ""),
        "Resmi Iddaa": "DOGRULANMADI",
        "Kimlik kontrolu": (
            "PROVIDER_BAGLANTISI_ONAYSIZ" if origin == "PROVIDER"
            else "KAYNAK_SAATI_BAGIMSIZ_DOGRULANMADI"
        ),
        "Mac durumu": status,
        "Model turu": "YOK",
        "Kalibrasyon": "DOGRULANMADI",
        "Diger pazarlar": "VERI_YOKSA_HESAPLANAMADI",
        "Aciklama": "Yeterli dogrulanmis takim/lig modeli yok",
    })
    if is_past or kick is None:
        out["Aciklama"] = "Baslamis mac veya baslama saati dogrulanamadi; yeni tahmin yok"
        return out

    data = None
    if origin == "PROVIDER":
        # Provider probabilities are ONLY shown when already linked by the
        # existing review pipeline; the link remains UNAPPROVED.
        if review and review.get("research_model") not in ("", "NONE"):
            if probability_triplet(review):
                data = review
                out["Model turu"] = "ESLESME_INCELEMESI_ONAYSIZ_" + review["research_model"]
                out["Aciklama"] = "Model kaynagi inceleme kuyruğu; kimlik/resmi fikstur onaysiz"
    else:
        if f.get("decision") == "MODEL_ONLY_NO_ODDS" and probability_triplet(f):
            data = f
            out["Model turu"] = "TAKIM_POISSON_DENEYSEL"
            out["Ev orneklem"] = f.get("n_home", "")
            out["Deplasman orneklem"] = f.get("n_away", "")
            out["Aciklama"] = "Takim orneklemi sinirli; sakatlik/oran/kadro ve kalibrasyon yok"
        elif fallback and fallback.get("baseline_status") == "LEAGUE_PRIOR_RESEARCH_ONLY":
            if probability_triplet(fallback):
                data = fallback
                out["Model turu"] = "LIG_ORTALAMASI_TAKIMA_OZEL_DEGIL"
                out["Aciklama"] = "Takim gucu yok; sadece tarihsel lig ortalamasi"
                out["Ev orneklem"] = fallback.get("league_sample", "")
                out["Deplasman orneklem"] = fallback.get("league_sample", "")

    if data:
        probs = probability_triplet(data)
        out["MS 1 %"], out["MS X %"], out["MS 2 %"] = [round(100 * x, 1) for x in probs]
        out["2.5 Ust %"] = market_percent(data.get("p_over25"))
        out["KG Var %"] = market_percent(data.get("p_btts"))
        best = max(range(3), key=lambda i: probs[i])
        out["MS tahmini"] = ("1", "X", "2")[best]
        out["Güven %"] = round(probs[best] * 100, 1)
        # This is the predicted outcome probability, NEVER a measured hit rate.
    return out


def build_rows(source, horizon, provider, fallback, combined, day, now):
    """Keep provider fixtures separate until explicit identity approval exists."""
    fallback_by_key = {fixture_key(f): f for f in fallback}
    review_by_id = {r.get("event_id"): r for r in combined if r.get("event_id")}
    merged = {}
    for origin, items in (("KAYNAK", source), ("KAYNAK_14GUN", horizon)):
        for f in items:
            key = fixture_key(f)
            # Prefer an available nonempty model over a model-less same-key row.
            current = merged.get(key)
            if current is None or (
                probability_triplet(f) and not probability_triplet(current[1])
            ):
                merged[key] = (origin, f)
    output = []
    for key, (origin, f) in merged.items():
        row = make_row(f, day, now, origin, fallback_by_key.get(key))
        if row:
            output.append(row)
    source_count = len(output)

    seen_provider = set()
    for p in provider:
        key = p.get("event_id") or (
            p.get("home"), p.get("away"), p.get("kickoff_istanbul")
        )
        if key in seen_provider:
            continue
        seen_provider.add(key)
        row = make_row(p, day, now, "PROVIDER", review=review_by_id.get(p.get("event_id")))
        if row:
            output.append(row)
    output.sort(key=lambda x: (x["Saat (TSI)"] or "99:99", x["Lig"], x["Ev sahibi"]))
    official_count = None  # No verified official complete bulletin was provided.
    summary = {
        "date": day,
        "as_of_istanbul": now.astimezone(IST).isoformat(),
        "source_rows_unique_by_exact_identity": source_count,
        "provider_rows_unverified": len(output) - source_count,
        "total_rows_including_unapproved_provider": len(output),
        "cross_source_identity_deduplicated": False,
        "official_iddaa_bulletin_count": official_count,
        "official_bulletin_coverage_percent": None,
        "future_rows": sum(r["Mac durumu"] == "BASLAMADI" for r in output),
        "rows_with_experimental_1x2": sum(bool(r["MS tahmini"]) for r in output),
        "rows_without_1x2": sum(not bool(r["MS tahmini"]) for r in output),
        "provider_review_probabilities": sum(
            bool(r["MS tahmini"]) and r["Kaynak"] == "PROVIDER" for r in output
        ),
        "odds_approved": 0,
        "betting_recommendations": 0,
        "confidence_column_meaning": "PREDICTED_OUTCOME_PROBABILITY_NOT_HISTORICAL_ACCURACY",
        "warning": (
            "Not an official complete Iddaa bulletin. Provider/source overlap is not "
            "automatically merged. All displayed probabilities are exploratory and "
            "uncalibrated; NO verified bookmaker odds or EV."
        ),
    }
    return output, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now(IST).date().isoformat())
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--source", default="reports/today/matches.csv")
    parser.add_argument("--horizon", default="reports/horizon/matches.csv")
    parser.add_argument("--provider", default="reports/today/provider_fixture_inventory.csv")
    parser.add_argument("--fallback", default="reports/horizon/league_prior_fallback.csv")
    parser.add_argument("--combined", default="reports/odds/combined_model_review.csv")
    parser.add_argument("--out", default="reports/full-fixture")
    args = parser.parse_args()
    now = local_kickoff(args.as_of) if args.as_of else datetime.now(timezone.utc)
    if now is None:
        raise SystemExit("--as-of requires timezone offset")
    output, summary = build_rows(
        read_rows(args.source), read_rows(args.horizon), read_rows(args.provider),
        read_rows(args.fallback), read_rows(args.combined), args.date, now
    )
    folder = Path(args.out)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "all_visible_matches.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(output)
    (folder / "coverage_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
