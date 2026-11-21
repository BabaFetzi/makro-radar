"""Tests: python -m unittest -v"""
import json
import sys
import types
import unittest
from unittest import mock

import numpy as np
import pandas as pd

import daten
import news
import pruefung
import signale


class TrendTest(unittest.TestCase):
    def test_aufwaerts_positiv_abwaerts_negativ(self):
        idx = pd.bdate_range("2020-01-01", periods=400)
        hoch = pd.Series(np.linspace(100, 200, 400), idx)
        runter = pd.Series(np.linspace(200, 100, 400), idx)
        self.assertGreater(signale.trend_komponenten(hoch)["trend"].iloc[-1], 0.5)
        self.assertLess(signale.trend_komponenten(runter)["trend"].iloc[-1], -0.5)

    def test_kein_blick_in_die_zukunft(self):
        """Signal von Tag t darf sich nicht ändern, wenn spätere Kurse dazukommen."""
        df = daten.demo_kurse()
        kurz = signale.trend_komponenten(df["SMI"].iloc[:-50])["trend"].iloc[-1]
        lang = signale.trend_komponenten(df["SMI"])["trend"].iloc[-51]
        self.assertAlmostEqual(kurz, lang)


class NewsTest(unittest.TestCase):
    def test_snb_nur_franken(self):
        a = news.analysiere_mit_schluesselwoertern([{"quelle": "x", "titel": "SNB senkt Leitzins", "link": "",
                                                    "zeit": pd.Timestamp.now(tz="UTC").isoformat()}])
        self.assertNotIn("Bitcoin", a["meldungen"][0]["wirkung"])
        self.assertGreater(a["meldungen"][0]["wirkung"]["EUR/CHF"], 0)

    def test_claude_antwort_wird_sauber_gelesen(self):
        meldungen = daten.demo_news()[:3]
        antwort_json = {"lage": "Test-Lage", "meldungen": [
            {"nr": 0, "wirkung": {"Gold": 1, "SMI": 5, "Fantasie-Asset": 2}, "konfidenz": 0.8, "begruendung": "ok"},
            {"nr": 99, "wirkung": {"Gold": 1}},  # ungültige Nummer -> ignorieren
        ]}
        block = types.SimpleNamespace(type="text", text="Hier: " + json.dumps(antwort_json))
        client = mock.MagicMock()
        client.messages.create.return_value = types.SimpleNamespace(content=[block])
        fake = types.SimpleNamespace(Anthropic=lambda: client)
        with mock.patch.dict(sys.modules, {"anthropic": fake}):
            a = news.analysiere_mit_claude(meldungen)
        self.assertEqual(a["lage"], "Test-Lage")
        self.assertEqual(len(a["meldungen"]), 1)
        self.assertEqual(a["meldungen"][0]["wirkung"], {"Gold": 1, "SMI": 2})  # begrenzt, Fantasie entfernt

    def test_fallback_ohne_key(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            a = news.analysiere(daten.demo_news(), "auto")
        self.assertEqual(a["modus"], "Schlüsselwörter")


class PruefungTest(unittest.TestCase):
    def test_backtest_und_live(self):
        df = daten.demo_kurse()
        bt = pruefung.backtest(df)
        self.assertEqual(len(bt), 13)
        log = [{"datum": str(d.date()), "name": "Gold", "score": 50, "kurs": float(df["Gold"].loc[d])}
               for d in df.index[-60:-25]]
        live = pruefung.live_trefferquote(log, df)
        self.assertGreater(live["geprueft"], 0)


if __name__ == "__main__":
    unittest.main()
