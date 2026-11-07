#!/usr/bin/env python3
"""Human-readable candidate fixture report; no automatic approvals."""
import argparse,csv,json
from collections import Counter
from pathlib import Path

def render(rows):
    lines=["# SPOR MÜDÜRÜ — Maç kimliği inceleme raporu","",
           "Bu rapor **otomatik maç onayı vermez**. Takım adları ve saat benzerliği tek başına yeterli değildir.","",
           f"**İncelenecek eşleşme:** {len(rows)} | **Onaylanan:** 0",""]
    for i,r in enumerate(rows,1):
        lines += [f"## {i}. {r['provider_home']} — {r['provider_away']}","",
                  f"- **API ligi:** `{r['provider_sport']}`",
                  f"- **Kaynak ligi:** `{r['source_league']}`",
                  f"- **Kaynak takım adları:** {r['source_home']} — {r['source_away']}",
                  f"- **API başlangıcı (UTC):** {r['provider_kickoff_utc']}",
                  f"- **Kaynak başlangıcı (İstanbul olarak yorumlanmış):** {r['source_kickoff_istanbul']}",
                  f"- **Saat farkı:** {r['delta_minutes']} dakika",
                  f"- **Lig kontrolü:** {r['league_review']}",
                  f"- **Saat kontrolü:** {r['time_review']}",
                  f"- **Çoklu aday:** kaynak={r['source_pairs_for_event']}, API={r['provider_events_for_source']}",
                  "- **Karar:** MANUEL DOĞRULAMA BEKLİYOR; ONAY YOK",""]
    if not rows:lines+=["İnceleme kuyruğunda eşleşme bulunamadı.",""]
    lines+=["## Onay öncesi kontrol","",
            "Bağımsız resmî fikstürden aynı organizasyon, ev/deplasman takımları, tarih ve saat dilimi teyit edilmeli.",
            "Farklı organizasyonlar, saat dilimi belirsizliği ve tekrarlanan karşılaşmalar manuel incelenmeli.",
            "Bu dosya onaylı eşleştirme tablosu değildir; oranlar ve EV hesaplamasına bağlanmaz.",""]
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--queue",default="reports/odds/fixture_review_queue.csv")
    p.add_argument("--out",default="reports/odds/fixture_review_report.md")
    a=p.parse_args()
    with open(a.queue,encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
    output=Path(a.out);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(render(rows),encoding="utf-8")
    print(json.dumps({"report":str(output),"candidates":len(rows),"approved":0,"leagues":dict(Counter(r["source_league"] for r in rows)),
        "fixtures":[{"provider_home":r["provider_home"],"provider_away":r["provider_away"],
                     "provider_sport":r["provider_sport"],"source_league":r["source_league"],
                     "provider_kickoff_utc":r["provider_kickoff_utc"],
                     "source_kickoff_istanbul":r["source_kickoff_istanbul"],
                     "delta_minutes":r["delta_minutes"],"league_review":r["league_review"],
                     "time_review":r["time_review"],"approved":"NO"} for r in rows]},ensure_ascii=False))
if __name__=="__main__":main()
