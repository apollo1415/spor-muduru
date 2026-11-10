#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SPOR MUDURU gunluk motor (v1).

Tek komutla: gunun BUTUN maclari icin sekiz uzmanin sayisal ciktisi, tahmin defteri
kaydi ve gecmis tahminlerin sonuclandirilmasi. Veri: open-matchday (acik CSV).

  python gunluk_motor.py gunluk  --data <open-matchday klasoru> [--date YYYY-MM-DD]
  python gunluk_motor.py backtest --data <open-matchday klasoru>

Model: lig ortalamasi x takimin (ic/dis saha) hucum orani x rakibin savunma orani.
Oranlar az macta lig ortalamasina buzulur (K sozde-mac). Ayni yapi gol, ilk yari gol,
korner, ilk yari korner, sut, isabetli sut ve kart icin kullanilir. Olasiliklar
motor.py'den (tek skor matrisi, negatif binom sayim) cikar. Veri yoksa alan bos kalir.
"""
import argparse, csv, glob, json, os, subprocess, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import motor

IST = ZoneInfo("Europe/Istanbul")
K = 30.0           # buzulme: sozde-mac sayisi (backtest ile secildi)
W_TOP = 0.3        # toplamin lig ortalamasindan sapmasina verilen agirlik (0=lig ort., 1=ham model)
MIN_LIG = 20       # lig ortalamasi icin en az mac
MIN_TAKIM = 3      # takim basina en az ic/dis saha maci
# olcu -> (ev alani, deplasman alani)
OLCU = {
    "gol": ("ft_home", "ft_away"), "iy_gol": ("ht_home", "ht_away"),
    "korner": ("home_corners", "away_corners"), "iy_korner": ("home_corners_1h", "away_corners_1h"),
    "sut": ("home_shots", "away_shots"), "isabet": ("home_target", "away_target"),
    "kart": (("home_yellow", "home_red"), ("away_yellow", "away_red")),
}
VMR_ONKABUL = {"korner": 1.3, "iy_korner": 1.2, "sut": 1.5, "isabet": 1.3, "kart": 1.2}
# backtestte sinanan sabit cizgiler
BT_CIZGI = {"korner": 9.5, "iy_korner": 4.5, "sut": 23.5, "isabet": 7.5, "kart": 4.5}


def fnum(x):
    try:
        return float(x) if x not in ("", None) else None
    except (TypeError, ValueError):
        return None


def deger_al(r, alan):
    if isinstance(alan, tuple):
        v = [fnum(r.get(a)) for a in alan]
        return None if v[0] is None else sum(x or 0.0 for x in v)
    return fnum(r.get(alan))


def veri_yukle(data):
    """{lig: (sonuclar[kronolojik], fikstur)}"""
    out = {}
    for d in sorted(glob.glob(os.path.join(data, "data", "*"))):
        lig = os.path.basename(d)
        def oku(ad):
            p = os.path.join(d, ad)
            if not os.path.exists(p):
                return []
            with open(p, encoding="utf-8-sig", newline="") as f:
                return list(csv.DictReader(f))
        res = [r for r in oku("results_2627.csv") if fnum(r.get("ft_home")) is not None and r.get("date")]
        res.sort(key=lambda r: (r.get("date", ""), r.get("time", "")))
        out[lig] = (res, oku("fixtures_2627.csv"))
    return out


class Durum:
    """Bir ligin 'o ana kadarki' birikimli istatistikleri (ileriye sizinti yok)."""

    def __init__(self):
        self.lig = defaultdict(lambda: [0, 0.0, 0.0, 0.0])      # olcu -> n, ev top, dep top, toplam^2
        self.t = defaultdict(lambda: [0, 0.0, 0.0])              # (olcu, takim, 'e'/'d') -> n, atilan, yenen
        self.n_mac = 0

    def ekle(self, r):
        self.n_mac += 1
        for olcu, (ea, da) in OLCU.items():
            e, d = deger_al(r, ea), deger_al(r, da)
            if e is None or d is None:
                continue
            L = self.lig[olcu]; L[0] += 1; L[1] += e; L[2] += d; L[3] += (e + d) ** 2
            a = self.t[(olcu, r["home"], "e")]; a[0] += 1; a[1] += e; a[2] += d
            b = self.t[(olcu, r["away"], "d")]; b[0] += 1; b[1] += d; b[2] += e

    def beklenen(self, olcu, ev, dep, k=None):
        k = K if k is None else k
        """(ev beklenen, dep beklenen, n_ev, n_dep, vmr) ya da None."""
        L = self.lig.get(olcu)
        if not L or L[0] < MIN_LIG:
            return None
        le, ld = L[1] / L[0], L[2] / L[0]
        if le <= 0 or ld <= 0:
            return None
        E = self.t.get((olcu, ev, "e")); D = self.t.get((olcu, dep, "d"))
        if not E or not D or E[0] < MIN_TAKIM or D[0] < MIN_TAKIM:
            return None
        # takimin genel (ic+dis) orani, saha-ozel oranin onseli olarak kullanilir
        def genel(takim):
            e = self.t.get((olcu, takim, "e"), [0, 0, 0]); d = self.t.get((olcu, takim, "d"), [0, 0, 0])
            bekl_at = e[0] * le + d[0] * ld; bekl_ye = e[0] * ld + d[0] * le
            return ((e[1] + d[1] + k * (le + ld) / 2) / (bekl_at + k * (le + ld) / 2),
                    (e[2] + d[2] + k * (le + ld) / 2) / (bekl_ye + k * (le + ld) / 2))
        ge_at, ge_ye = genel(ev); gd_at, gd_ye = genel(dep)
        h = k / 2.0
        ev_at = (E[1] + h * le * ge_at) / (E[0] * le + h * le)      # evde atma orani
        ev_ye = (E[2] + h * ld * ge_ye) / (E[0] * ld + h * ld)      # evde yeme orani
        dp_at = (D[1] + h * ld * gd_at) / (D[0] * ld + h * ld)
        dp_ye = (D[2] + h * le * gd_ye) / (D[0] * le + h * le)
        be = max(0.05, le * ev_at * dp_ye); bd = max(0.05, ld * dp_at * ev_ye)
        # taraf (oran) bilgisi korunur; toplam, lig ortalamasina dogru cekilir
        f = ((le + ld) / (be + bd)) ** (1.0 - W_TOP)
        be *= f; bd *= f
        ort = (L[1] + L[2]) / L[0]; var = L[3] / L[0] - ort ** 2
        vmr = max(1.0, min(2.5, var / ort)) if L[0] >= 60 and ort > 0 else VMR_ONKABUL.get(olcu, 1.0)
        return be, bd, E[0], D[0], vmr


def tahmin(S, ev, dep, cizgiler=None):
    """Bir mac icin tum pazarlar. S: ligin o ana kadarki Durum'u."""
    z = {}
    g = S.beklenen("gol", ev, dep)
    if not g:
        return z
    lh, la = g[0], g[1]
    z.update(lam_ev=round(lh, 3), lam_dep=round(la, 3), n_ev=g[2], n_dep=g[3])
    gp = motor.gol_pazarlari(lh, la)
    z["gol"] = {k: round(v, 4) for k, v in gp.items() if k != "SKORLAR"}
    z["skorlar"] = [(s, round(p, 4)) for s, p in gp["SKORLAR"][:5]]
    m = motor.skor_matrisi(lh, la)
    ar = {"0-1": 0.0, "2-3": 0.0, "4+": 0.0}
    for h in range(len(m)):
        for a in range(len(m)):
            ar["0-1" if h + a <= 1 else ("2-3" if h + a <= 3 else "4+")] += m[h][a]
    z["gol_araligi"] = {k: round(v, 4) for k, v in ar.items()}
    iy = S.beklenen("iy_gol", ev, dep)
    pay, pay_kaynak = 0.45, "on-kabul"
    if iy and (lh + la) > 0:
        pay = max(0.30, min(0.60, (iy[0] + iy[1]) / (lh + la))); pay_kaynak = "veri"
    dv = motor.devre_pazarlari(lh, la, pay)
    z["devre"] = {k: round(v, 4) for k, v in dv.items() if k != "IYMS"}
    z["iyms"] = {k: round(v, 4) for k, v in sorted(dv["IYMS"].items(), key=lambda t: -t[1])}
    z["iy_pay"] = (round(pay, 3), pay_kaynak)
    for olcu in ("korner", "sut", "isabet", "kart", "iy_korner"):
        b = S.beklenen(olcu, ev, dep)
        if not b:
            continue
        top = b[0] + b[1]
        cz = (cizgiler or {}).get(olcu)
        if not cz:
            c0 = int(top) + 0.5
            cz = (c0 - 1, c0, c0 + 1) if c0 >= 1.5 else (c0, c0 + 1)
        sp = motor.sayim_pazari(b[0], b[1], b[4], cz)
        z[olcu] = {"bekl_ev": round(b[0], 2), "bekl_dep": round(b[1], 2), "n_ev": b[2], "n_dep": b[3],
                   "vmr": round(b[4], 2), **{k: round(v, 4) for k, v in sp.items()}}
    return z


# ---------------------------------------------------------------- backtest
def backtest(veri, k=K, yaz=None):
    """Yuruyen pencere: her mac yalniz kendinden ONCEKI maclarla tahmin edilir."""
    kayit = defaultdict(list)       # pazar -> [(p, y, taban_p)]
    for lig, (res, _) in veri.items():
        S = Durum(); taban = defaultdict(lambda: [0, 0])
        i = 0
        while i < len(res):
            j = i
            while j < len(res) and res[j]["date"] == res[i]["date"]:
                j += 1
            for r in res[i:j]:      # ayni gunun maclari birbirini gormez
                z = tahmin(S, r["home"], r["away"], {o: (c,) for o, c in BT_CIZGI.items()}) if S.n_mac >= 30 else {}
                h, a = fnum(r["ft_home"]), fnum(r["ft_away"])
                olay = {}
                if z:
                    olay = {"MS1": (z["gol"]["MS1"], h > a), "MSX": (z["gol"]["MSX"], h == a), "MS2": (z["gol"]["MS2"], h < a),
                            "UST_2.5": (z["gol"]["UST_2.5"], h + a > 2.5), "KG_VAR": (z["gol"]["KG_VAR"], h > 0 and a > 0)}
                    hh, ha = fnum(r.get("ht_home")), fnum(r.get("ht_away"))
                    if hh is not None and ha is not None and z["iy_pay"][1] == "veri":
                        olay["IY_UST_1.5"] = (z["devre"]["IY_UST_1.5"], hh + ha > 1.5)
                        olay["IY_UST_0.5"] = (z["devre"]["IY_UST_0.5"], hh + ha > 0.5)
                    for o, c in BT_CIZGI.items():
                        e, d = deger_al(r, OLCU[o][0]), deger_al(r, OLCU[o][1])
                        if o in z and e is not None and d is not None:
                            olay["%s_UST_%s" % (o, c)] = (z[o]["UST_%s" % c], e + d > c)
                for ad, (p, y) in olay.items():
                    t = taban[ad]
                    if t[0] >= 20:
                        kayit[ad].append((p, 1.0 if y else 0.0, t[1] / t[0]))
                # taban oran: tahmin yapilsin yapilmasin, ayni olayin ligdeki gecmis sikligi
                hh, ha = fnum(r.get("ht_home")), fnum(r.get("ht_away"))
                gercek = {"MS1": h > a, "MSX": h == a, "MS2": h < a, "UST_2.5": h + a > 2.5, "KG_VAR": h > 0 and a > 0}
                if hh is not None and ha is not None:
                    gercek["IY_UST_1.5"] = hh + ha > 1.5; gercek["IY_UST_0.5"] = hh + ha > 0.5
                for o, c in BT_CIZGI.items():
                    e, d = deger_al(r, OLCU[o][0]), deger_al(r, OLCU[o][1])
                    if e is not None and d is not None:
                        gercek["%s_UST_%s" % (o, c)] = e + d > c
                r["_gercek"] = gercek
            for r in res[i:j]:
                S.ekle(r)
                for ad, y in r.pop("_gercek").items():
                    taban[ad][0] += 1; taban[ad][1] += 1.0 if y else 0.0
            i = j
    ozet = {}
    for ad, v in sorted(kayit.items()):
        n = len(v)
        br = sum((p - y) ** 2 for p, y, _ in v) / n
        bt = sum((t - y) ** 2 for _, y, t in v) / n
        ozet[ad] = {"n": n, "brier_model": round(br, 4), "brier_taban": round(bt, 4),
                    "beceri": round(1 - br / bt, 4) if bt > 0 else None,
                    "gozlenen": round(sum(y for _, y, _ in v) / n, 4), "ort_tahmin": round(sum(p for p, _, _ in v) / n, 4)}
    if yaz:
        os.makedirs(os.path.dirname(yaz) or ".", exist_ok=True)
        with open(yaz, "w", encoding="utf-8") as f:
            json.dump({"yontem": "yuruyen pencere, yalniz onceki gunler; taban = ligin o ana kadarki sikligi",
                       "K": k, "uretim": datetime.now(IST).isoformat(timespec="minutes"), "pazarlar": ozet}, f, ensure_ascii=False, indent=1)
    return ozet


# ---------------------------------------------------------------- gunluk
UZMAN = {  # uzman -> (bolum, aday seciciler)
    "Mac Sonucu": lambda z: _en("gol", z, ("MS1", "MSX", "MS2")),
    "Alt/Ust": lambda z: _en("gol", z, ("UST_2.5", "ALT_2.5", "KG_VAR", "KG_YOK", "UST_1.5", "ALT_3.5")),
    "Skor": lambda z: (("skor " + z["skorlar"][0][0], z["skorlar"][0][1]) if z.get("skorlar") else None),
    "IY": lambda z: _en("devre", z, ("IY1", "IYX", "IY2", "IY_UST_0.5")),
    "Korner": lambda z: _cizgi("korner", z),
    "Sut": lambda z: _cizgi("sut", z),
    "Kart": lambda z: _cizgi("kart", z),
    "IY/MS Korner": lambda z: _cizgi("iy_korner", z),
}


def _en(bolum, z, adlar):
    b = z.get(bolum)
    if not b:
        return None
    ad = max(adlar, key=lambda a: b.get(a, 0))
    return ad, b[ad]


def _cizgi(olcu, z):
    b = z.get(olcu)
    if not b:
        return None
    aday = [(k, v) for k, v in b.items() if k.startswith(("UST_", "ALT_"))]
    # yazi-turaya en uzak ama asiri uc olmayan cizgi (0,55-0,80 arasi tercih)
    iyi = [x for x in aday if 0.55 <= x[1] <= 0.80] or aday
    k, v = max(iyi, key=lambda t: t[1])
    return "%s %s" % (olcu, k), v


def karne_oku(yol):
    if not os.path.exists(yol):
        return {}
    with open(yol, encoding="utf-8") as f:
        return json.load(f).get("pazarlar", {})


BT_ANAHTAR = {"Mac Sonucu": ("MS1", "MSX", "MS2"), "Alt/Ust": ("UST_2.5", "KG_VAR"), "IY": ("IY_UST_0.5", "IY_UST_1.5"),
              "Korner": ("korner_UST_9.5",), "Sut": ("sut_UST_23.5",), "Kart": ("kart_UST_4.5",),
              "IY/MS Korner": ("iy_korner_UST_4.5",), "Skor": ("MS1", "MSX", "MS2")}


def guven(uzman, n_min, bt, kupa):
    """A-D. Geriye donuk beceri (taban orani gecme) + orneklem. Kupa/lig-disi eslesme en fazla C."""
    anahtar = [bt[a] for a in BT_ANAHTAR.get(uzman, ()) if a in bt]
    n_bt = min((x["n"] for x in anahtar), default=0)
    beceri = sum(x["beceri"] for x in anahtar) / len(anahtar) if anahtar else None
    puan = (2 if n_min >= 10 else 1 if n_min >= 6 else 0)
    if beceri is not None and n_bt >= 100:
        puan += 3 if beceri >= 0.03 else 2 if beceri >= 0.01 else 0 if beceri >= 0 else -2
    harf = "A" if puan >= 5 else "B" if puan >= 3 else "C" if puan >= 1 else "D"
    if harf == "A":
        harf = "B"      # A yalniz ileriye donuk karne (defter) 100+ sonuca ulasinca verilecek
    if (kupa or uzman == "Skor") and harf == "B":
        harf = "C"      # tam skor dusuk olasilikli bir secimdir; kupa/lig-disi profil zayif
    return harf


def gunluk(veri, tarih, cikti, simdi):
    bt = backtest(veri, yaz=os.path.join(cikti, "..", "backtest.json"))
    bugun = datetime.fromisoformat(tarih).date()
    maclar = []
    # takimin 'ana ligi': kupa maclarinda oradan profil alinir
    ana = {}
    durumlar = {}
    for lig, (res, _) in veri.items():
        S = Durum()
        for r in res:
            if r["date"] < tarih:
                S.ekle(r)
        durumlar[lig] = S
        if "_CUP_" in lig or lig.startswith("UEFA"):
            continue
        say = defaultdict(int)
        for r in res:
            say[r["home"]] += 1; say[r["away"]] += 1
        for t, n in say.items():
            if n > ana.get(t, (None, 0))[1]:
                ana[t] = (lig, n)
    for lig, (_, fx) in veri.items():
        for f in fx:
            saat, ko, durum = "?", None, "baslamadi"
            if f.get("time"):
                try:    # kaynak sabit UTC+1 saat kullanir
                    ko = datetime.strptime(f["date"] + " " + f["time"], "%Y-%m-%d %H:%M").replace(
                        tzinfo=timezone(timedelta(hours=1))).astimezone(IST)
                except ValueError:
                    ko = None
            if ko:
                if ko.date() != bugun:
                    continue
                saat = ko.strftime("%H:%M")
                if ko <= simdi:
                    durum = "basladi/bitti"
            elif f.get("date") != tarih:
                continue
            ev, dep = f.get("home"), f.get("away")
            m = {"lig": lig, "saat": saat, "ev": ev, "dep": dep, "durum": durum, "notlar": []}
            if not f.get("time"):
                m["notlar"].append("baslama saati kaynakta yok")
            z = tahmin(durumlar[lig], ev, dep)
            kupa = False
            if not z:
                le, ld = ana.get(ev), ana.get(dep)
                if le and ld and le[0] == ld[0]:
                    z = tahmin(durumlar[le[0]], ev, dep)
                    if z:
                        m["notlar"].append("profil %s liginden alindi" % le[0]); kupa = True
                elif le and ld:
                    m["notlar"].append("takimlar farkli liglerden (%s / %s): lig gucu farki modellenemedi" % (le[0], ld[0]))
            if not z:
                m["sonuc"] = "hesaplanamadi"
                if len(m["notlar"]) == (0 if f.get("time") else 1):
                    m["notlar"].append("yeterli gecmis mac yok")
            else:
                m["model"] = z
                n_min = min(z["n_ev"], z["n_dep"])
                m["uzmanlar"] = {}
                for u, sec in UZMAN.items():
                    s = sec(z)
                    if not s:
                        m["uzmanlar"][u] = None
                        continue
                    nm = n_min
                    for olcu in ("korner", "sut", "kart", "iy_korner"):
                        if s[0].startswith(olcu + " "):
                            nm = min(z[olcu]["n_ev"], z[olcu]["n_dep"])
                    m["uzmanlar"][u] = {"secim": s[0], "olasilik": round(100 * s[1], 1), "n": nm, "guven": guven(u, nm, bt, kupa)}
            maclar.append(m)
    maclar.sort(key=lambda m: (m["saat"] == "?", m["saat"], m["lig"], m["ev"]))
    os.makedirs(cikti, exist_ok=True)
    ozet = {"tarih": tarih, "kesit": simdi.isoformat(timespec="minutes"), "kaynak": "oladeeayo/open-matchday",
            "envanter": len(maclar), "modellenen": sum("model" in m for m in maclar),
            "hesaplanamadi": sum("model" not in m for m in maclar),
            "baslamis": sum(m["durum"] != "baslamadi" for m in maclar), "maclar": maclar}
    with open(os.path.join(cikti, tarih + ".json"), "w", encoding="utf-8") as f:
        json.dump(ozet, f, ensure_ascii=False, indent=1)
    with open(os.path.join(cikti, tarih + ".md"), "w", encoding="utf-8") as f:
        f.write(md_yaz(ozet, bt))
    return ozet, bt


def md_yaz(o, bt):
    s = ["# Spor Muduru veri paketi - %s" % o["tarih"], "",
         "Kesit %s | envanter %d | modellenen %d | hesaplanamadi %d | baslamis %d | kaynak %s" % (
             o["kesit"], o["envanter"], o["modellenen"], o["hesaplanamadi"], o["baslamis"], o["kaynak"]), "",
         "## Geriye donuk karne (yuruyen pencere; beceri>0 = taban orandan iyi)", "",
         "| pazar | n | Brier model | Brier taban | beceri |", "|---|---|---|---|---|"]
    s += ["| %s | %d | %.4f | %.4f | %+.1f%% |" % (k, v["n"], v["brier_model"], v["brier_taban"], 100 * v["beceri"]) for k, v in bt.items()]
    s += ["", "## Maclar", ""]
    for m in o["maclar"]:
        s.append("### %s  %s - %s  (%s)%s" % (m["saat"], m["ev"], m["dep"], m["lig"], "  [BASLADI/BITTI]" if m["durum"] != "baslamadi" else ""))
        if m["notlar"]:
            s.append("Not: " + "; ".join(m["notlar"]))
        if "model" not in m:
            s += ["hesaplanamadi", ""]
            continue
        z = m["model"]; g = z["gol"]
        s.append("lam %.2f-%.2f (n %d/%d) | MS %.0f/%.0f/%.0f | U2.5 %.0f | KG %.0f | skor %s | IY %.0f/%.0f/%.0f | IY/MS %s" % (
            z["lam_ev"], z["lam_dep"], z["n_ev"], z["n_dep"], 100 * g["MS1"], 100 * g["MSX"], 100 * g["MS2"], 100 * g["UST_2.5"], 100 * g["KG_VAR"],
            ", ".join("%s %.0f" % (a, 100 * b) for a, b in z["skorlar"][:3]),
            100 * z["devre"]["IY1"], 100 * z["devre"]["IYX"], 100 * z["devre"]["IY2"],
            ", ".join("%s %.0f" % (a, 100 * b) for a, b in list(z["iyms"].items())[:3])))
        for olcu in ("korner", "iy_korner", "sut", "isabet", "kart"):
            if olcu in z:
                b = z[olcu]
                s.append("%s: bekl %.1f+%.1f=%.1f (n %d/%d) | %s" % (olcu, b["bekl_ev"], b["bekl_dep"], b["BEKLENEN"], b["n_ev"], b["n_dep"],
                         ", ".join("%s %.0f" % (k, 100 * v) for k, v in b.items() if k.startswith("UST_"))))
        s.append("Uzman secimleri: " + " | ".join(
            "%s: %s" % (u, ("%s %%%.0f [%s]" % (x["secim"], x["olasilik"], x["guven"])) if x else "hesaplanamadi") for u, x in m["uzmanlar"].items()))
        s.append("")
    return "\n".join(s)


# ---------------------------------------------------------------- defter
DEFTER_ALAN = ["tarih", "kayit_zamani", "lig", "ev", "dep", "saat", "uzman", "secim", "olasilik", "guven", "sonuc"]


def defter_oku(yol):
    if not os.path.exists(yol):
        return []
    with open(yol, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def defter_yaz(yol, satirlar):
    os.makedirs(os.path.dirname(yol) or ".", exist_ok=True)
    with open(yol, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DEFTER_ALAN); w.writeheader(); w.writerows(satirlar)


def secim_tuttu_mu(secim, r):
    """True/False/None(veri yok)."""
    h, a = fnum(r.get("ft_home")), fnum(r.get("ft_away"))
    hh, ha = fnum(r.get("ht_home")), fnum(r.get("ht_away"))
    if h is None or a is None:
        return None
    basit = {"MS1": h > a, "MSX": h == a, "MS2": h < a, "KG_VAR": h > 0 and a > 0, "KG_YOK": not (h > 0 and a > 0)}
    if secim in basit:
        return basit[secim]
    if secim.startswith("skor "):
        return secim[5:] == "%d-%d" % (h, a)
    if secim.startswith(("UST_", "ALT_")):
        c = float(secim[4:]); return (h + a > c) if secim[0] == "U" else (h + a < c)
    if secim.startswith("IY"):
        if hh is None or ha is None:
            return None
        if secim.startswith("IY_UST_"):
            return hh + ha > float(secim[7:])
        return {"IY1": hh > ha, "IYX": hh == ha, "IY2": hh < ha}.get(secim)
    for olcu in ("iy_korner", "korner", "sut", "isabet", "kart"):
        if secim.startswith(olcu + " "):
            e, d = deger_al(r, OLCU[olcu][0]), deger_al(r, OLCU[olcu][1])
            if e is None or d is None:
                return None
            yon, c = secim.split(" ")[1].split("_"); c = float(c)
            return (e + d > c) if yon == "UST" else (e + d < c)
    return None


def defter_guncelle(veri, ozet, yol, karne_yol, simdi):
    satirlar = defter_oku(yol)
    # 1) bekleyenleri sonuclandir
    idx = {}
    for lig, (res, _) in veri.items():
        for r in res:
            idx[(lig, r["date"], r["home"], r["away"])] = r
    for s in satirlar:
        if s["sonuc"] != "bekliyor":
            continue
        r = None
        for g in (0, 1, -1):    # kaynak tarihi TSI gununden bir gun kayabilir
            t = (datetime.fromisoformat(s["tarih"]).date() + timedelta(days=g)).isoformat()
            r = idx.get((s["lig"], t, s["ev"], s["dep"])) or r
        if r is None:
            if (simdi.date() - datetime.fromisoformat(s["tarih"]).date()).days > 10:
                s["sonuc"] = "sonuc_bulunamadi"
            continue
        y = secim_tuttu_mu(s["secim"], r)
        s["sonuc"] = "veri_yok" if y is None else ("tuttu" if y else "tutmadi")
    # 2) bugunun secimlerini ekle (bir kez; yalniz baslamamis ve guven A/B/C)
    var = {(s["tarih"], s["lig"], s["ev"], s["dep"], s["uzman"]) for s in satirlar}
    for m in ozet["maclar"]:
        if m["durum"] != "baslamadi" or "uzmanlar" not in m:
            continue
        for u, x in m["uzmanlar"].items():
            if not x or x["guven"] == "D" or (ozet["tarih"], m["lig"], m["ev"], m["dep"], u) in var:
                continue
            satirlar.append({"tarih": ozet["tarih"], "kayit_zamani": simdi.isoformat(timespec="minutes"), "lig": m["lig"], "ev": m["ev"],
                             "dep": m["dep"], "saat": m["saat"], "uzman": u, "secim": x["secim"], "olasilik": x["olasilik"],
                             "guven": x["guven"], "sonuc": "bekliyor"})
    defter_yaz(yol, satirlar)
    # 3) ileriye donuk karne
    k = defaultdict(lambda: [0, 0, 0.0, 0.0])
    for s in satirlar:
        if s["sonuc"] in ("tuttu", "tutmadi"):
            for anahtar in (s["uzman"], s["uzman"] + " / guven " + s["guven"], "TOPLAM"):
                p = float(s["olasilik"]) / 100; y = 1.0 if s["sonuc"] == "tuttu" else 0.0
                a = k[anahtar]; a[0] += 1; a[1] += y; a[2] += p; a[3] += (p - y) ** 2
    L = ["# Ileriye donuk karne", "", "Guncelleme: %s. Yalniz mac ONCESI kaydedilmis ve sonuclanmis tahminler." % simdi.isoformat(timespec="minutes"), "",
         "| uzman | n | tuttu | isabet % | ort. verilen olasilik % | Brier |", "|---|---|---|---|---|---|"]
    for ad in sorted(k):
        n, y, p, b = k[ad]
        L.append("| %s | %d | %d | %.1f | %.1f | %.3f |" % (ad, n, y, 100 * y / n, 100 * p / n, b / n))
    bekleyen = sum(s["sonuc"] == "bekliyor" for s in satirlar)
    L += ["", "Bekleyen tahmin: %d. Toplam kayit: %d." % (bekleyen, len(satirlar))]
    with open(karne_yol, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return len(satirlar), bekleyen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["gunluk", "backtest"])
    ap.add_argument("--data", default=None, help="open-matchday klasoru; verilmezse /tmp'ye klonlanir")
    ap.add_argument("--date", default=None)
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--out", default="raporlar/gunluk")
    ap.add_argument("--defter", default="defter/tahminler.csv")
    ap.add_argument("--no-defter", action="store_true")
    a = ap.parse_args()
    data = a.data
    if not data:
        data = "/tmp/open-matchday"
        if not os.path.isdir(os.path.join(data, "data")):
            subprocess.run(["git", "clone", "--depth", "1", "-q", "https://github.com/oladeeayo/open-matchday", data], check=True)
    veri = veri_yukle(data)
    if not veri:
        sys.exit("veri bulunamadi: " + data)
    simdi = datetime.fromisoformat(a.as_of).astimezone(IST) if a.as_of else datetime.now(IST)
    if a.mod == "backtest":
        o = backtest(veri, K, yaz=os.path.join(a.out, "..", "backtest.json"))
        for p, v in o.items():
            print("%-22s n=%-5d brier %.4f taban %.4f beceri %+.1f%%" % (p, v["n"], v["brier_model"], v["brier_taban"], 100 * v["beceri"]))
        if False:
            print( " ".join("%s:%+.1f%%" % (p, 100 * v["beceri"]) for p, v in o.items()))
        return
    tarih = a.date or simdi.date().isoformat()
    ozet, _ = gunluk(veri, tarih, a.out, simdi)
    msg = {k: ozet[k] for k in ("tarih", "kesit", "envanter", "modellenen", "hesaplanamadi", "baslamis")}
    if not a.no_defter:
        msg["defter_kayit"], msg["defter_bekleyen"] = defter_guncelle(
            veri, ozet, a.defter, os.path.join(os.path.dirname(a.defter) or ".", "karne.md"), simdi)
    print(json.dumps(msg, ensure_ascii=False))


if __name__ == "__main__":
    main()
