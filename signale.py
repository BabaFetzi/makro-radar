"""Signalberechnung: Trend/Momentum + Makro-Umfeld + News -> Gesamtscore −100…+100.

Trend und Makro werden für die ganze Historie berechnet, damit der Backtest exakt
dieselbe Logik prüft, die heute das Signal erzeugt.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config


def _clip(x, grenze=1.0):
    return np.clip(x, -grenze, grenze)


# ------------------------------------------------------------------ Komponenten

def trend_komponenten(p: pd.Series) -> pd.DataFrame:
    sma50, sma200 = p.rolling(50).mean(), p.rolling(200).mean()
    vola = np.log(p).diff().rolling(63).std() * np.sqrt(252)
    abstand = p / sma200 - 1
    kreuz = sma50 / sma200 - 1
    mom12 = p.shift(21) / p.shift(252) - 1                     # 12 Monate ohne letzten Monat
    mom3 = p / p.shift(63) - 1
    return pd.DataFrame({
        "abstand_sma200": abstand,
        "mom12": mom12,
        "mom3": mom3,
        "vola": vola,
        "trend": pd.concat([
            _clip(abstand / 0.05),
            _clip(kreuz / 0.03),
            _clip(mom12 / vola.replace(0, np.nan)),
            _clip(mom3 / (vola * 0.5).replace(0, np.nan)),
        ], axis=1).mean(axis=1, skipna=False),
    })


def makro_umfeld(df: pd.DataFrame) -> pd.DataFrame:
    vix = df["VIX"]
    kurve = df["US10J"] - df["US3M"]
    vix_niveau = _clip((20 - vix) / 8)
    vix_trend = _clip(-(vix / vix.rolling(50).mean() - 1) / 0.25)
    kurven_signal = _clip(kurve / 1.0) * 0.5
    risiko = 0.45 * vix_niveau + 0.35 * vix_trend + 0.20 * kurven_signal
    dollar = _clip((df["DOLLAR"] / df["DOLLAR"].rolling(100).mean() - 1) / 0.03)
    return pd.DataFrame({"risiko": risiko, "dollar": dollar, "vix": vix, "zinskurve": kurve})


def makro_fuer_asset(umfeld: pd.DataFrame, klasse: str) -> pd.Series:
    return _clip(config.RISIKO_SENSITIVITAET[klasse] * umfeld["risiko"]
                 + config.DOLLAR_SENSITIVITAET[klasse] * umfeld["dollar"])


def kombiniere(trend, makro, news=None):
    g = config.GEWICHTE
    if news is None:  # z.B. im Backtest: News-Gewicht auf die anderen verteilen
        return 100 * (g["trend"] * trend + g["makro"] * makro) / (g["trend"] + g["makro"])
    return 100 * (g["trend"] * trend + g["makro"] * makro + g["news"] * news)


def label(score: float) -> str:
    s = config.SCHWELLEN
    if score >= s["stark"]:
        return "Stark positiv"
    if score >= s["normal"]:
        return "Positiv"
    if score <= -s["stark"]:
        return "Stark negativ"
    if score <= -s["normal"]:
        return "Negativ"
    return "Neutral"


def _pct(x):
    return f"{x * 100:+.1f}%"


# ------------------------------------------------------------------ Aktuelles Signal pro Anlage

def aktuelle_signale(df: pd.DataFrame, news_score: dict) -> tuple[list[dict], dict]:
    umfeld = makro_umfeld(df)
    jetzt = umfeld.dropna().iloc[-1]
    ergebnisse = []

    for name, a in config.ASSETS.items():
        p = df[name].dropna()
        if len(p) < 260:
            continue
        tk = trend_komponenten(p).iloc[-1]
        makro = float(makro_fuer_asset(umfeld, a["klasse"]).reindex(p.index).ffill().iloc[-1])
        trend = float(tk["trend"])
        ns = news_score.get(name, {"score": 0.0, "anzahl": 0, "top": []})
        score = float(kombiniere(trend, makro, ns["score"]))

        teile = [("Trend", trend), ("Makro", makro)] + ([("News", ns["score"])] if ns["anzahl"] else [])
        gleiche_richtung = sum(1 for _, v in teile if np.sign(v) == np.sign(score) and abs(v) > 0.1)
        konfidenz = "hoch" if gleiche_richtung == len(teile) and abs(score) >= 30 else \
                    "mittel" if gleiche_richtung >= len(teile) - 1 else "niedrig"

        gruende = [
            f"Kurs {_pct(tk['abstand_sma200'])} zum 200-Tage-Schnitt "
            f"({'Aufwärtstrend' if tk['abstand_sma200'] > 0 else 'Abwärtstrend'})",
            f"Momentum: 3 Monate {_pct(tk['mom3'])}, 12 Monate {_pct(tk['mom12'])}",
        ]
        if abs(makro) > 0.15:
            gruende.append(f"Makro-Umfeld {'stützt' if makro > 0 else 'belastet'} diese Anlageklasse")
        if ns["anzahl"]:
            richtung = "positiv" if ns["score"] > 0.1 else "negativ" if ns["score"] < -0.1 else "gemischt"
            gruende.append(f"{ns['anzahl']} relevante Meldung(en), Tendenz {richtung}")

        verlauf = p.iloc[-90:]
        ergebnisse.append({
            "name": name, "gruppe": a["gruppe"], "kurs": float(p.iloc[-1]),
            "veraenderung_1t": float(p.iloc[-1] / p.iloc[-2] - 1),
            "veraenderung_1m": float(p.iloc[-1] / p.iloc[-22] - 1),
            "score": round(score), "label": label(score), "konfidenz": konfidenz,
            "komponenten": {"trend": round(trend * 100), "makro": round(makro * 100), "news": round(ns["score"] * 100)},
            "gruende": gruende, "news_top": ns["top"],
            "verlauf": [round(float(v), 6) for v in verlauf.to_numpy()],
            "vola": float(tk["vola"]),
        })

    risiko = float(jetzt["risiko"])
    umfeld_info = {
        "risiko": round(risiko * 100),
        "regime": "Risk-on" if risiko > 0.2 else "Risk-off" if risiko < -0.2 else "Neutral",
        "vix": round(float(jetzt["vix"]), 1),
        "zinskurve": round(float(jetzt["zinskurve"]), 2),
        "us10j": round(float(df["US10J"].dropna().iloc[-1]), 2),
        "dollar_trend": round(float(jetzt["dollar"]) * 100),
        "datum": str(df.index[-1].date()),
    }
    return ergebnisse, umfeld_info
