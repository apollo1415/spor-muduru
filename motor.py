# -*- coding: utf-8 -*-
"""SPOR MUDURU - ortak olasilik motoru (v1.0)
Tum uzman ajanlar AYNI motoru kullanir; boylece pazarlar birbiriyle celismez.
Sadece standart kutuphane. Girdi yoksa fonksiyon cagrilmaz -> 'hesaplanamadi'.
"""
from math import exp, lgamma, log

def pois(k, lam):
    return exp(-lam + k * log(lam) - lgamma(k + 1)) if lam > 0 else (1.0 if k == 0 else 0.0)

def negbin(k, mean, vmr):
    """vmr = varyans/ortalama. vmr<=1.02 ise Poisson'a duser."""
    if vmr <= 1.02:
        return pois(k, mean)
    r = mean / (vmr - 1.0); p = r / (r + mean)
    return exp(lgamma(k + r) - lgamma(r) - lgamma(k + 1) + r * log(p) + k * log(1 - p))

def skor_matrisi(lh, la, rho=-0.08, n=11):
    """Dixon-Coles duzeltmeli skor matrisi; kesme artigi normalize edilir."""
    def tau(h, a):
        if h == 0 and a == 0: return 1 - lh * la * rho
        if h == 0 and a == 1: return 1 + lh * rho
        if h == 1 and a == 0: return 1 + la * rho
        if h == 1 and a == 1: return 1 - rho
        return 1.0
    m = [[max(pois(h, lh) * pois(a, la) * tau(h, a), 0.0) for a in range(n)] for h in range(n)]
    s = sum(map(sum, m))
    return [[x / s for x in r] for r in m]

def gol_pazarlari(lh, la, rho=-0.08):
    """MS 1X2, cifte sans, alt/ust, KG, en olasi skorlar - TEK matristen."""
    m = skor_matrisi(lh, la, rho); n = len(m)
    c = [(h, a, m[h][a]) for h in range(n) for a in range(n)]
    p1 = sum(p for h, a, p in c if h > a); px = sum(p for h, a, p in c if h == a); p2 = 1 - p1 - px
    out = {"MS1": p1, "MSX": px, "MS2": p2, "CS_1X": p1 + px, "CS_12": p1 + p2, "CS_X2": px + p2,
           "KG_VAR": sum(p for h, a, p in c if h > 0 and a > 0)}
    out["KG_YOK"] = 1 - out["KG_VAR"]
    for line in (0.5, 1.5, 2.5, 3.5, 4.5):
        u = sum(p for h, a, p in c if h + a > line)
        out["UST_%s" % line] = u; out["ALT_%s" % line] = 1 - u
    out["SKORLAR"] = [("%d-%d" % (h, a), p) for h, a, p in sorted(c, key=lambda t: -t[2])[:6]]
    return out

def devre_pazarlari(lh, la, iy_pay=0.45, rho=-0.08, n=8):
    """IY 1X2, IY alt/ust ve 9'lu IY/MS. Iki yari ayri surec, MS = IY + 2Y toplami
    (bagimsiz carpim DEGIL, ortak dagilim). iy_pay: gollerin ilk yariya dusen payi."""
    iy = skor_matrisi(lh * iy_pay, la * iy_pay, rho, n)
    y2 = skor_matrisi(lh * (1 - iy_pay), la * (1 - iy_pay), 0.0, n)
    s = lambda d: "1" if d > 0 else ("X" if d == 0 else "2")
    out = {"IY1": 0.0, "IYX": 0.0, "IY2": 0.0, "IY_UST_0.5": 0.0, "IY_UST_1.5": 0.0}
    komb = {a + "/" + b: 0.0 for a in "1X2" for b in "1X2"}
    d2 = {}
    for h in range(n):
        for a in range(n):
            d2[h - a] = d2.get(h - a, 0.0) + y2[h][a]
    for h in range(n):
        for a in range(n):
            p = iy[h][a]; out["IY" + s(h - a)] += p
            if h + a > 0.5: out["IY_UST_0.5"] += p
            if h + a > 1.5: out["IY_UST_1.5"] += p
            for d, q in d2.items():
                komb[s(h - a) + "/" + s(h - a + d)] += p * q
    # MS marji, gol matrisindeki MS 1X2 ile birebir ayni olsun (pazarlar arasi tutarlilik)
    g = gol_pazarlari(lh, la, rho); hedef = {"1": g["MS1"], "X": g["MSX"], "2": g["MS2"]}
    for b in "1X2":
        t = sum(komb[a + "/" + b] for a in "1X2")
        for a in "1X2":
            komb[a + "/" + b] *= hedef[b] / t
    out["IYMS"] = komb
    return out

def sayim_pazari(ort_ev, ort_dep, vmr=1.3, cizgiler=(8.5, 9.5, 10.5), iy_pay=None):
    """Korner / kart / sut gibi sayim pazarlari. ort_*: beklenen sayilar (veriden!).
    vmr: toplamin varyans/ortalama orani (veriden; yoksa korner~1.3, kart~1.2, sut~1.5 ON-KABUL
    ve raporda 'on-kabul' diye isaretlenir). iy_pay verilirse ilk yari cizgileri de doner."""
    top = ort_ev + ort_dep
    def ust(mean, line):
        return 1 - sum(negbin(k, mean, vmr) for k in range(int(line) + 1))
    out = {"BEKLENEN": top}
    for c in cizgiler:
        u = ust(top, c); out["UST_%s" % c] = u; out["ALT_%s" % c] = 1 - u
    # taraf: hangi takim daha cok (Skellam yaklasimi, Poisson)
    pe = sum(pois(i, ort_ev) * sum(pois(j, ort_dep) for j in range(i)) for i in range(40))
    pb = sum(pois(i, ort_ev) * pois(i, ort_dep) for i in range(40))
    out["EV_COK"] = pe; out["ESIT"] = pb; out["DEP_COK"] = 1 - pe - pb
    if iy_pay:
        m = top * iy_pay; out["IY_BEKLENEN"] = m
        for c in (3.5, 4.5, 5.5):
            out["IY_UST_%s" % c] = ust(m, c)
    return out

def marj_arindir(oranlar):
    """Guc (power) yontemi: sum((1/o)^k) = 1. Oransal yonteme gore favori-surpriz
    yanliligini daha az tasir. Doner: (olasiliklar, marj)."""
    q = [1.0 / o for o in oranlar]; marj = sum(q) - 1
    lo, hi = 0.5, 3.0
    for _ in range(60):
        k = (lo + hi) / 2
        if sum(x ** k for x in q) > 1: lo = k
        else: hi = k
    return [x ** k for x in q], marj

def deger(model_p, iddaa_orani):
    """Beklenen deger (EV). >0 ise oran, modele gore 'degerli'."""
    return model_p * iddaa_orani - 1

def guven_notu(mac_orneklem, kaynak_sayisi, model_piyasa_farki, karne_n=0, karne_brier_iyi=None):
    """Olasilik != Guven. Guven = bu olasiliga ne kadar yaslanilabilir (A/B/C/D).
    mac_orneklem: takim basina kullanilan mac sayisi (min); kaynak_sayisi: bagimsiz veri kaynagi;
    model_piyasa_farki: |model - marjsiz piyasa| (0-1); karne: bu uzman+pazar icin sonuclanmis tahmin
    sayisi ve Brier'in taban orandan iyi olup olmadigi (Backtest Mudurlugu verir)."""
    puan = 0
    puan += 2 if mac_orneklem >= 10 else (1 if mac_orneklem >= 6 else 0)
    puan += 1 if kaynak_sayisi >= 2 else 0
    puan += 1 if model_piyasa_farki <= 0.07 else (0 if model_piyasa_farki <= 0.12 else -1)
    if karne_n >= 100 and karne_brier_iyi is True: puan += 2
    elif karne_n >= 100 and karne_brier_iyi is False: puan -= 2
    harf = "A" if puan >= 5 else ("B" if puan >= 3 else ("C" if puan >= 1 else "D"))
    if karne_n < 100 and harf == "A": harf = "B"   # karne olmadan A verilmez
    return harf

if __name__ == "__main__":
    g = gol_pazarlari(1.55, 1.10); d = devre_pazarlari(1.55, 1.10)
    assert abs(g["MS1"] + g["MSX"] + g["MS2"] - 1) < 1e-9
    assert abs(sum(d["IYMS"].values()) - 1) < 1e-6
    ms1_iyms = sum(v for k, v in d["IYMS"].items() if k.endswith("/1"))
    print("MS1 %.3f X %.3f MS2 %.3f | UST2.5 %.3f KG %.3f" % (g["MS1"], g["MSX"], g["MS2"], g["UST_2.5"], g["KG_VAR"]))
    print("Skorlar:", [(s, round(p, 3)) for s, p in g["SKORLAR"]])
    print("IY 1/X/2: %.3f %.3f %.3f | IYMS toplam MS1=%.3f (matris MS1=%.3f)" % (d["IY1"], d["IYX"], d["IY2"], ms1_iyms, g["MS1"]))
    print("IYMS:", {k: round(v, 3) for k, v in d["IYMS"].items()})
    k = sayim_pazari(5.4, 4.3, 1.3, iy_pay=0.47); print("Korner:", {a: round(b, 3) for a, b in k.items()})
    c = sayim_pazari(2.1, 2.4, 1.2, cizgiler=(3.5, 4.5, 5.5)); print("Kart:", {a: round(b, 3) for a, b in c.items()})
    p, m = marj_arindir([1.85, 3.40, 3.60]); print("Devig:", [round(x, 3) for x in p], "marj %.3f" % m, "EV %.3f" % deger(g["MS1"], 1.85))
    print("Guven:", guven_notu(12, 2, abs(g["MS1"] - p[0])), guven_notu(4, 1, 0.15), guven_notu(12, 2, 0.03, 150, True))
