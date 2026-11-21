"""Aktien-Empfehlungen: Rangliste aus Momentum, Qualität/Bewertung und Makro-Sektor-Fit.

Ergebnis ist eine begründete Rangliste – keine persönliche Anlageberatung.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import signale

# ------------------------------------------------------------------ Universum
# (Name, Yahoo-Ticker, Sektor)
UNIVERSUM = {
    "Schweiz": [
        ("Nestlé", "NESN.SW", "basiskonsum"), ("Novartis", "NOVN.SW", "gesundheit"),
        ("Roche", "ROG.SW", "gesundheit"), ("UBS", "UBSG.SW", "finanz"),
        ("ABB", "ABBN.SW", "industrie"), ("Zurich Insurance", "ZURN.SW", "finanz"),
        ("Richemont", "CFR.SW", "zykl_konsum"), ("Sika", "SIKA.SW", "rohstoffe"),
        ("Lonza", "LONN.SW", "gesundheit"), ("Holcim", "HOLN.SW", "rohstoffe"),
        ("Alcon", "ALC.SW", "gesundheit"), ("Givaudan", "GIVN.SW", "rohstoffe"),
        ("Partners Group", "PGHN.SW", "finanz"), ("Swiss Re", "SREN.SW", "finanz"),
        ("Swiss Life", "SLHN.SW", "finanz"), ("Kühne+Nagel", "KNIN.SW", "industrie"),
        ("Geberit", "GEBN.SW", "industrie"), ("Swisscom", "SCMN.SW", "kommunikation"),
        ("Sonova", "SOON.SW", "gesundheit"), ("Logitech", "LOGN.SW", "tech"),
    ],
    "USA": [
        ("Apple", "AAPL", "tech"), ("Microsoft", "MSFT", "tech"), ("Nvidia", "NVDA", "tech"),
        ("Amazon", "AMZN", "zykl_konsum"), ("Alphabet", "GOOGL", "kommunikation"),
        ("Meta", "META", "kommunikation"), ("Broadcom", "AVGO", "tech"), ("Tesla", "TSLA", "zykl_konsum"),
        ("Berkshire Hathaway", "BRK-B", "finanz"), ("JPMorgan", "JPM", "finanz"), ("Visa", "V", "finanz"),
        ("Mastercard", "MA", "finanz"), ("UnitedHealth", "UNH", "gesundheit"), ("Eli Lilly", "LLY", "gesundheit"),
        ("Johnson & Johnson", "JNJ", "gesundheit"), ("ExxonMobil", "XOM", "energie"), ("Chevron", "CVX", "energie"),
        ("Procter & Gamble", "PG", "basiskonsum"), ("Coca-Cola", "KO", "basiskonsum"), ("PepsiCo", "PEP", "basiskonsum"),
        ("Costco", "COST", "basiskonsum"), ("Walmart", "WMT", "basiskonsum"), ("Home Depot", "HD", "zykl_konsum"),
        ("Merck", "MRK", "gesundheit"), ("AbbVie", "ABBV", "gesundheit"), ("Oracle", "ORCL", "tech"),
        ("Salesforce", "CRM", "tech"), ("AMD", "AMD", "tech"), ("Netflix", "NFLX", "kommunikation"),
        ("Caterpillar", "CAT", "industrie"),
    ],
    "Europa": [
        ("ASML", "ASML.AS", "tech"), ("SAP", "SAP.DE", "tech"), ("LVMH", "MC.PA", "zykl_konsum"),
        ("Siemens", "SIE.DE", "industrie"), ("Novo Nordisk", "NOVO-B.CO", "gesundheit"),
        ("TotalEnergies", "TTE.PA", "energie"), ("Airbus", "AIR.PA", "industrie"), ("Allianz", "ALV.DE", "finanz"),
        ("L'Oréal", "OR.PA", "basiskonsum"), ("Sanofi", "SAN.PA", "gesundheit"), ("Hermès", "RMS.PA", "zykl_konsum"),
        ("Schneider Electric", "SU.PA", "industrie"), ("Deutsche Telekom", "DTE.DE", "kommunikation"),
        ("Iberdrola", "IBE.MC", "versorger"), ("Shell", "SHEL.L", "energie"), ("AstraZeneca", "AZN.L", "gesundheit"),
        ("HSBC", "HSBA.L", "finanz"), ("Unilever", "ULVR.L", "basiskonsum"), ("BNP Paribas", "BNP.PA", "finanz"),
        ("Enel", "ENEL.MI", "versorger"),
    ],
    "ETFs": [
        ("US-Technologie", "XLK", "tech"), ("US-Finanzen", "XLF", "finanz"), ("US-Energie", "XLE", "energie"),
        ("US-Gesundheit", "XLV", "gesundheit"), ("US-Industrie", "XLI", "industrie"),
        ("US-Basiskonsum", "XLP", "basiskonsum"), ("US-Versorger", "XLU", "versorger"),
        ("US-Zyklischer Konsum", "XLY", "zykl_konsum"), ("US-Rohstoffe", "XLB", "rohstoffe"),
        ("Europa gesamt", "VGK", "markt"), ("Japan", "EWJ", "markt"), ("Schwellenländer", "EEM", "markt"),
    ],
}

SEKTOR_NAMEN = {"tech": "Technologie", "finanz": "Finanzen", "energie": "Energie", "gesundheit": "Gesundheit",
                "basiskonsum": "Basiskonsum", "zykl_konsum": "Zyklischer Konsum", "industrie": "Industrie",
                "rohstoffe": "Rohstoffe/Chemie", "versorger": "Versorger", "kommunikation": "Kommunikation",
                "markt": "Breiter Markt"}

# Wie reagiert ein Sektor auf Risk-on(+)/off(−), steigende Zinsen(+) und steigenden Ölpreis(+)?
SEKTOR_MAKRO = {
    #               risiko  zinsen  öl
    "tech":         (1.0,  -0.6,  -0.2),
    "zykl_konsum":  (0.9,  -0.4,  -0.4),
    "kommunikation": (0.7, -0.3,  -0.1),
    "industrie":    (0.8,  -0.2,  -0.2),
    "finanz":       (0.7,   0.6,   0.0),
    "rohstoffe":    (0.6,  -0.1,   0.2),
    "energie":      (0.3,   0.1,   1.0),
    "markt":        (0.8,  -0.2,   0.0),
    "gesundheit":   (-0.2, -0.2,  -0.1),
    "basiskonsum":  (-0.5, -0.3,  -0.2),
    "versorger":    (-0.6, -0.7,  -0.1),
}

GEWICHTE = {"momentum": 0.40, "qualitaet": 0.35, "makro": 0.25}
TOP_N = 10


def alle_titel() -> list[dict]:
    return [{"name": n, "ticker": t, "sektor": s, "gruppe": g}
            for g, liste in UNIVERSUM.items() for n, t, s in liste]


# ------------------------------------------------------------------ Daten

def lade_kurse(jahre: int = 6) -> pd.DataFrame:
    import yfinance as yf

    titel = alle_titel()
    roh = yf.download([t["ticker"] for t in titel], period=f"{jahre}y", interval="1d",
                      auto_adjust=True, progress=False, threads=True)
    close = roh["Close"] if isinstance(roh.columns, pd.MultiIndex) else roh
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    return close[~close.index.duplicated(keep="last")].sort_index()


def lade_fundamentaldaten(cache: Path, max_alter_tage: int = 7) -> dict[str, dict]:
    """Kennzahlen pro Aktie. Wird wöchentlich aktualisiert (schont Yahoo und spart Zeit)."""
    if cache.exists():
        daten = json.loads(cache.read_text())
        if datetime.fromisoformat(daten["stand"]) > datetime.now() - timedelta(days=max_alter_tage):
            return daten["werte"]
    import yfinance as yf

    felder = ["trailingPE", "forwardPE", "priceToBook", "returnOnEquity", "profitMargins",
              "debtToEquity", "dividendYield", "revenueGrowth", "earningsGrowth"]
    werte = {}
    for t in alle_titel():
        if t["gruppe"] == "ETFs":
            continue
        try:
            info = yf.Ticker(t["ticker"]).info
            werte[t["ticker"]] = {f: info.get(f) for f in felder}
        except Exception as e:
            print(f"  Fundamentaldaten {t['ticker']}: {e}")
        time.sleep(0.3)
    cache.write_text(json.dumps({"stand": datetime.now().isoformat(), "werte": werte}))
    return werte


# ------------------------------------------------------------------ Faktoren

def _z(s: pd.Series) -> pd.Series:
    """Robuster z-Wert (Median/IQR), begrenzt auf ±3. Fehlende Werte = 0 (neutral)."""
    s = s.astype(float)
    mitte, iqr = s.median(), s.quantile(0.75) - s.quantile(0.25)
    if not np.isfinite(iqr) or iqr == 0:
        return pd.Series(0.0, index=s.index)
    return ((s - mitte) / (iqr / 1.35)).clip(-3, 3).fillna(0.0)


def momentum_roh(p: pd.DataFrame) -> pd.DataFrame:
    """Für alle Tage: 12-1-Monats-Momentum und 6-Monats-Momentum, jeweils risikobereinigt, plus Trendfilter."""
    vola = np.log(p).diff().rolling(126, min_periods=60).std() * np.sqrt(252)
    m12 = (p.shift(21) / p.shift(252) - 1) / vola
    m6 = (p / p.shift(126) - 1) / vola
    ueber200 = (p > p.rolling(200, min_periods=150).mean()).astype(float) * 2 - 1
    return m12, m6, ueber200, vola


def momentum_score(p: pd.DataFrame, tag=None) -> pd.Series:
    m12, m6, ueber200, _ = momentum_roh(p)
    i = -1 if tag is None else p.index.get_loc(tag)
    return 0.5 * _z(m12.iloc[i]) + 0.3 * _z(m6.iloc[i]) + 0.2 * ueber200.iloc[i].fillna(0)


def qualitaet_score(fund: dict[str, dict], ticker: list[str]) -> tuple[pd.Series, pd.DataFrame]:
    felder = ["trailingPE", "forwardPE", "priceToBook", "returnOnEquity", "profitMargins",
              "debtToEquity", "dividendYield", "revenueGrowth", "earningsGrowth"]
    df = pd.DataFrame({t: fund.get(t) or {} for t in ticker}).T.reindex(index=ticker, columns=felder)
    df = df.apply(pd.to_numeric, errors="coerce")
    # Bewertung: günstiger = besser (Gewinnrendite statt KGV, damit negative Gewinne nicht "günstig" wirken)
    pe = df["forwardPE"].where(df["forwardPE"] > 0, df["trailingPE"])
    gewinnrendite = (1 / pe).where(pe > 0)
    qualitaet = (_z(df["returnOnEquity"].clip(-1, 1)) + _z(df["profitMargins"].clip(-1, 1))
                 - 0.5 * _z(df["debtToEquity"].clip(0, 500))) / 2.5
    bewertung = 0.7 * _z(gewinnrendite) + 0.3 * _z(-df["priceToBook"].clip(0, 50))
    wachstum = _z(df["earningsGrowth"].clip(-1, 2))
    score = 0.45 * qualitaet + 0.35 * bewertung + 0.20 * wachstum
    vorhanden = df.notna().sum(axis=1) >= 3
    return score.where(vorhanden, 0.0), df


def makro_trends(makro_df: pd.DataFrame) -> pd.DataFrame:
    """Risiko-Umfeld, Zins-Trend und Öl-Trend für alle Tage (−1…+1)."""
    umfeld = signale.makro_umfeld(makro_df)
    zins = makro_df["US10J"]
    zins_trend = np.clip((zins - zins.rolling(100, min_periods=50).mean()) / 0.4, -1, 1)
    oel = makro_df["Öl (WTI)"]
    oel_trend = np.clip((oel / oel.rolling(100, min_periods=50).mean() - 1) / 0.1, -1, 1)
    return pd.DataFrame({"risiko": umfeld["risiko"], "zinsen": zins_trend, "oel": oel_trend}).ffill()


def makro_fit(sektoren: pd.Series, lage: pd.Series) -> pd.Series:
    werte = {t: SEKTOR_MAKRO[s][0] * lage["risiko"] + SEKTOR_MAKRO[s][1] * lage["zinsen"] + SEKTOR_MAKRO[s][2] * lage["oel"]
             for t, s in sektoren.items()}
    return pd.Series(werte).clip(-1.5, 1.5) * 2  # auf ähnliche Skala wie z-Werte bringen


# ------------------------------------------------------------------ Rangliste

def rangliste(kurse: pd.DataFrame, fund: dict, makro_df: pd.DataFrame) -> tuple[list[dict], dict]:
    titel = {t["ticker"]: t for t in alle_titel()}
    p = kurse[[t for t in titel if t in kurse]].dropna(axis=1, thresh=300).ffill(limit=3)
    ticker = list(p.columns)
    sektoren = pd.Series({t: titel[t]["sektor"] for t in ticker})

    mom = momentum_score(p)
    qual, kennzahlen = qualitaet_score(fund, ticker)
    lage = makro_trends(makro_df).dropna().iloc[-1]
    mak = makro_fit(sektoren, lage)

    ist_etf = pd.Series({t: titel[t]["gruppe"] == "ETFs" for t in ticker})
    g = GEWICHTE
    gesamt = g["momentum"] * mom + g["qualitaet"] * qual + g["makro"] * mak
    # ETFs haben keine Fundamentaldaten: Gewicht auf Momentum und Makro verteilen
    gesamt[ist_etf] = (g["momentum"] * mom + g["makro"] * mak)[ist_etf] / (g["momentum"] + g["makro"])
    perzentil = gesamt.rank(pct=True) * 100

    m12, m6, ueber200, vola = momentum_roh(p)
    ergebnisse = []
    for t in ticker:
        k = kennzahlen.loc[t] if t in kennzahlen.index else pd.Series(dtype=float)
        perf12 = float(p[t].iloc[-1] / p[t].iloc[-253] - 1) if len(p) > 253 else None
        gruende = []
        if perf12 is not None:
            gruende.append(f"12 Monate {perf12 * 100:+.0f}%, Kurs {'über' if ueber200[t].iloc[-1] > 0 else 'unter'} 200-Tage-Schnitt")
        pe = k.get("forwardPE") if pd.notna(k.get("forwardPE", np.nan)) else k.get("trailingPE")
        if pd.notna(pe) and pe and pe > 0:
            gruende.append(f"KGV {pe:.0f}" + (" (günstig)" if qual[t] > 0.5 and pe < 18 else " (teuer)" if pe > 35 else ""))
        roe = k.get("returnOnEquity")
        if pd.notna(roe):
            gruende.append(f"Eigenkapitalrendite {roe * 100:.0f}%")
        if abs(mak[t]) > 0.6:
            gruende.append(f"Makro-Umfeld {'begünstigt' if mak[t] > 0 else 'belastet'} {SEKTOR_NAMEN[sektoren[t]]}")
        div = k.get("dividendYield")
        if pd.notna(div) and div:
            div = div if div < 1 else div / 100   # yfinance liefert je nach Version 0.03 oder 3.0
            if div >= 0.025:
                gruende.append(f"Dividende {div * 100:.1f}%")

        ergebnisse.append({
            "name": titel[t]["name"], "ticker": t, "gruppe": titel[t]["gruppe"],
            "sektor": SEKTOR_NAMEN[sektoren[t]], "score": round(float(perzentil[t])),
            "momentum": round(float(mom[t]), 2), "qualitaet": None if ist_etf[t] else round(float(qual[t]), 2),
            "makro": round(float(mak[t]), 2), "perf12": perf12, "vola": float(vola[t].iloc[-1]),
            "kurs": float(p[t].iloc[-1]), "gruende": gruende,
            "verlauf": [round(float(v), 4) for v in p[t].iloc[-126:].to_numpy()],
        })
    ergebnisse.sort(key=lambda e: -e["score"])
    return ergebnisse, {k: round(float(v), 2) for k, v in lage.items()}


def markt_ampel(makro_df: pd.DataFrame, umfeld: dict) -> dict:
    """Soll man überhaupt neu investieren? Einfache, transparente Regel."""
    spx = makro_df["S&P 500"].dropna()
    ueber200 = spx.iloc[-1] > spx.rolling(200).mean().iloc[-1]
    if umfeld["regime"] == "Risk-off" and not ueber200:
        return {"farbe": "rot", "text": "Markt im Abwärtstrend und Stress-Modus. Neue Käufe nur gestaffelt "
                "(z.B. in 3–4 Tranchen über Wochen), defensive Titel bevorzugen, Cash-Reserve halten."}
    if umfeld["regime"] == "Risk-off" or not ueber200:
        return {"farbe": "gelb", "text": "Gemischtes Bild. Gestaffelt einsteigen, nicht alles auf einmal."}
    return {"farbe": "grün", "text": "Intaktes Umfeld. Die Rangliste ist aussagekräftiger als in Stressphasen."}


# ------------------------------------------------------------------ Backtest

def backtest(kurse: pd.DataFrame, makro_df: pd.DataFrame, top_n: int = TOP_N, kosten: float = 0.002) -> dict:
    """Monatlich die Top-N nach Momentum + Makro kaufen (gleich gewichtet), einen Monat halten.
    Fundamentaldaten fehlen historisch und fliessen daher NICHT ein."""
    titel = {t["ticker"]: t for t in alle_titel() if t["gruppe"] != "ETFs"}
    p = kurse[[t for t in titel if t in kurse]].dropna(axis=1, thresh=300).ffill(limit=3)
    sektoren = pd.Series({t: titel[t]["sektor"] for t in p.columns})
    trends = makro_trends(makro_df).reindex(p.index).ffill()
    m12, m6, ueber200, _ = momentum_roh(p)

    monatsenden = p.resample("ME").last().index
    monatsenden = [p.index[p.index.get_indexer([d], method="ffill")[0]] for d in monatsenden]
    monatsenden = [d for d in monatsenden if p.index.get_loc(d) >= 260]

    renditen_s, renditen_alle, vorher = [], [], set()
    for a, b in zip(monatsenden[:-1], monatsenden[1:]):
        lage = trends.loc[a]
        if lage.isna().any():
            continue
        mom = 0.5 * _z(m12.loc[a]) + 0.3 * _z(m6.loc[a]) + 0.2 * ueber200.loc[a].fillna(0)
        score = (GEWICHTE["momentum"] * mom + GEWICHTE["makro"] * makro_fit(sektoren, lage))
        score = score[p.loc[a].notna() & p.loc[b].notna()]
        top = set(score.nlargest(top_n).index)
        r = (p.loc[b] / p.loc[a] - 1)
        umschlag = len(top - vorher) / top_n
        renditen_s.append(float(r[list(top)].mean()) - umschlag * kosten * 2)
        renditen_alle.append(float(r[score.index].mean()))
        vorher = top

    if len(renditen_s) < 12:
        return {}
    s, alle = pd.Series(renditen_s), pd.Series(renditen_alle)
    kurve_s, kurve_a = (1 + s).cumprod(), (1 + alle).cumprod()
    jahre = len(s) / 12
    return {
        "monate": len(s),
        "cagr_top": float(kurve_s.iloc[-1] ** (1 / jahre) - 1),
        "cagr_alle": float(kurve_a.iloc[-1] ** (1 / jahre) - 1),
        "maxdd_top": float((kurve_s / kurve_s.cummax() - 1).min()),
        "maxdd_alle": float((kurve_a / kurve_a.cummax() - 1).min()),
        "monate_besser": float((s > alle).mean()),
    }
