import unittest
import motor
import gunluk_motor as g


def mac(d, h, a, fh, fa, **k):
    r = {"date": d, "time": "15:00", "home": h, "away": a, "ft_home": str(fh), "ft_away": str(fa)}
    r.update({x: str(y) for x, y in k.items()})
    return r


class MotorTest(unittest.TestCase):
    def test_pazarlar_tutarli(self):
        gp = motor.gol_pazarlari(1.6, 1.1)
        self.assertAlmostEqual(gp["MS1"] + gp["MSX"] + gp["MS2"], 1.0, places=9)
        dv = motor.devre_pazarlari(1.6, 1.1)
        self.assertAlmostEqual(sum(dv["IYMS"].values()), 1.0, places=6)
        self.assertAlmostEqual(sum(v for k, v in dv["IYMS"].items() if k.endswith("/1")), gp["MS1"], places=6)

    def test_veri_yoksa_bos(self):
        self.assertEqual(g.tahmin(g.Durum(), "A", "B"), {})

    def test_guclu_takim_favori(self):
        S = g.Durum()
        takim = ["A", "B", "C", "D", "E", "F"]
        for tur in range(6):
            for i, h in enumerate(takim):
                a = takim[(i + 1 + tur) % 6]
                if a == h:
                    continue
                S.ekle(mac("2026-09-%02d" % (tur + 1), h, a, 3 if h == "A" else (0 if a == "A" else 1), 3 if a == "A" else (0 if h == "A" else 1)))
        z = g.tahmin(S, "A", "B")
        self.assertGreater(z["gol"]["MS1"], z["gol"]["MS2"])

    def test_sonuclandirma(self):
        r = mac("2026-09-01", "A", "B", 2, 2, ht_home=0, ht_away=0, home_corners=8, away_corners=1,
                home_yellow=1, away_yellow=0, home_red=0, away_red=0)
        self.assertTrue(g.secim_tuttu_mu("MSX", r))
        self.assertTrue(g.secim_tuttu_mu("skor 2-2", r))
        self.assertFalse(g.secim_tuttu_mu("IY_UST_0.5", r))
        self.assertTrue(g.secim_tuttu_mu("korner ALT_9.5", r))
        self.assertTrue(g.secim_tuttu_mu("kart ALT_2.5", r))
        self.assertIsNone(g.secim_tuttu_mu("sut UST_20.5", r))


if __name__ == "__main__":
    unittest.main()
