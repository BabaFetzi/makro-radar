"""Datenbeschaffung: Kurse (Yahoo Finance), Makrodaten (optional FRED) und Demo-Daten."""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

import config


def lade_kurse(jahre: int = 6) -> pd.DataFrame:
    """Tagesschlusskurse aller Assets und Indikatoren als Tabelle (Spalten = Namen)."""
    import yfinance as yf

    tickers = {name: a["ticker"] for name, a in config.ASSETS.items()} | config.INDIKATOREN
    roh = yf.download(list(tickers.values()), period=f"{jahre}y", interval="1d",
                      auto_adjust=True, progress=False, threads=True)
    close = roh["Close"] if isinstance(roh.columns, pd.MultiIndex) else roh
    umbenennen = {t: n for n, t in tickers.items()}
    df = close.rename(columns=umbenennen)[list(tickers)]
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    # Krypto handelt am Wochenende, Börsen nicht. Nur die Makro-Indikatoren auffüllen;
    # Anlagekurse bleiben roh, sonst entstehen künstliche 0%-Tage (z.B. "SMI +0.00%" am Samstag).
    ind = list(config.INDIKATOREN)
    df[ind] = df[ind].ffill(limit=5)
    return df


def lade_fred() -> dict[str, dict]:
    """Optionale US-Makrodaten. Gibt {} zurück, wenn kein API-Key vorhanden ist."""
    key = os.getenv("FRED_API_KEY")
    if not key:
        return {}
    import requests

    ergebnis = {}
    for name, serie in config.FRED_SERIEN.items():
        try:
            r = requests.get("https://api.stlouisfed.org/fred/series/observations", timeout=20, params={
                "series_id": serie, "api_key": key, "file_type": "json",
                "sort_order": "desc", "limit": 14})
            r.raise_for_status()
            werte = [(o["date"], float(o["value"])) for o in r.json()["observations"] if o["value"] != "."]
            if serie == "CPIAUCSL" and len(werte) >= 13:
                aktuell = (werte[0][1] / werte[12][1] - 1) * 100
                vormonat = (werte[1][1] / werte[13][1] - 1) * 100 if len(werte) >= 14 else None
            else:
                aktuell, vormonat = werte[0][1], (werte[1][1] if len(werte) > 1 else None)
            ergebnis[name] = {"wert": round(aktuell, 2), "vorher": None if vormonat is None else round(vormonat, 2),
                              "datum": werte[0][0]}
        except Exception as e:  # eine fehlende Serie soll nicht alles stoppen
            print(f"  FRED {serie}: {e}")
    return ergebnis


# ------------------------------------------------------------------ Demo-Modus (ohne Internet)

def demo_kurse(tage: int = 1500, seed: int = 7) -> pd.DataFrame:
    """Realistisch wirkende, aber künstliche Kurse mit Marktphasen – nur zum Testen."""
    rng = np.random.default_rng(seed)
    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=tage)

    # gemeinsamer Risikofaktor mit Regimewechseln (ruhig / Stress)
    regime = np.zeros(tage)
    stress = False
    for i in range(tage):
        if rng.random() < (0.02 if stress else 0.006):
            stress = not stress
        regime[i] = 1 if stress else 0
    markt = np.where(regime == 1, rng.normal(-0.0015, 0.02, tage), rng.normal(0.0006, 0.008, tage))

    start = {"SMI": 11000, "S&P 500": 4500, "DAX": 16000, "Nasdaq": 14000, "EUR/CHF": 0.97, "USD/CHF": 0.89,
             "EUR/USD": 1.08, "USD/JPY": 145, "Gold": 2000, "Öl (WTI)": 78, "Kupfer": 3.9,
             "Bitcoin": 40000, "Ethereum": 2300}
    daten = {}
    for name, a in config.ASSETS.items():
        beta = config.RISIKO_SENSITIVITAET[a["klasse"]]
        vola = {"krypto": 0.03, "zyklisch_rohstoff": 0.016, "gold": 0.009, "aktien": 0.007}.get(a["klasse"], 0.004)
        skala = 0.35 if a["klasse"].startswith("fx") else 1.0
        rendite = beta * markt * skala + rng.normal(0.0002, vola, tage)
        daten[name] = start[name] * np.exp(np.cumsum(rendite))

    vix = 15 + regime * 14 + np.abs(rng.normal(0, 2.5, tage))
    daten["VIX"] = pd.Series(vix).rolling(5, min_periods=1).mean().to_numpy()
    daten["US10J"] = 4.2 + np.cumsum(rng.normal(0, 0.03, tage))
    daten["US3M"] = 4.6 + np.cumsum(rng.normal(-0.0004, 0.02, tage))
    daten["DOLLAR"] = 104 * np.exp(np.cumsum(-0.3 * markt + rng.normal(0, 0.003, tage)))
    return pd.DataFrame(daten, index=index)


def demo_news() -> list[dict]:
    jetzt = pd.Timestamp.now(tz="UTC")
    titel = [
        ("Fed (US-Notenbank)", "Federal Reserve signals possible rate cut as inflation cools"),
        ("CNBC Wirtschaft", "US inflation falls more than expected in October"),
        ("Google News: Geopolitik", "OPEC+ agrees to extend oil production cuts into next year"),
        ("Google News: Geopolitik", "New US tariffs on Chinese imports spark trade war fears"),
        ("Google News: Schweiz", "SNB senkt Leitzins – Franken schwächt sich ab"),
        ("CoinDesk", "Bitcoin ETF inflows hit record as institutional demand grows"),
        ("CNBC Top News", "Copper prices jump on strong China manufacturing data"),
        ("MarketWatch", "Tech stocks rally after strong earnings from chipmakers"),
        ("EZB", "ECB keeps interest rates unchanged, warns of recession risks"),
        ("Google News: Geopolitik", "Tensions escalate in Middle East, gold climbs to record high"),
    ]
    return [{"quelle": q, "titel": t, "link": "", "zeit": (jetzt - pd.Timedelta(hours=i * 3)).isoformat()}
            for i, (q, t) in enumerate(titel)]


def demo_aktien(index: pd.DatetimeIndex, seed: int = 11) -> tuple[pd.DataFrame, dict]:
    """Künstliche Aktienkurse und Kennzahlen für den Demo-Modus."""
    import aktien

    rng = np.random.default_rng(seed)
    markt = rng.normal(0.0004, 0.009, len(index))
    kurse, fund = {}, {}
    for t in aktien.alle_titel():
        drift = rng.normal(0.0003, 0.0004)
        r = rng.uniform(0.6, 1.3) * markt + rng.normal(drift, rng.uniform(0.008, 0.022), len(index))
        kurse[t["ticker"]] = 100 * np.exp(np.cumsum(r))
        if t["gruppe"] != "ETFs":
            fund[t["ticker"]] = {"trailingPE": float(rng.uniform(8, 45)), "forwardPE": float(rng.uniform(8, 40)),
                                 "priceToBook": float(rng.uniform(1, 12)), "returnOnEquity": float(rng.uniform(-0.05, 0.4)),
                                 "profitMargins": float(rng.uniform(0.02, 0.35)), "debtToEquity": float(rng.uniform(0, 250)),
                                 "dividendYield": float(rng.uniform(0, 0.05)), "revenueGrowth": float(rng.uniform(-0.1, 0.3)),
                                 "earningsGrowth": float(rng.uniform(-0.3, 0.5))}
    return pd.DataFrame(kurse, index=index), fund
