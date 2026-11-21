"""Ehrlichkeits-Check: Backtest der Kurs-/Makro-Signale und Live-Trefferquote der echten Signale."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import config
import signale

KOSTEN = 0.001  # 0.1 % pro Ein- oder Ausstieg


def _max_drawdown(kurve: pd.Series) -> float:
    return float((kurve / kurve.cummax() - 1).min())


def _cagr(kurve: pd.Series, tage_pro_jahr: float) -> float:
    jahre = len(kurve) / tage_pro_jahr
    return float(kurve.iloc[-1] ** (1 / jahre) - 1) if jahre > 0 and kurve.iloc[-1] > 0 else 0.0


def backtest(df: pd.DataFrame) -> dict[str, dict]:
    """Strategie: investiert, wenn Score > 0, sonst Cash. Signal von heute wirkt erst ab morgen
    (kein Blick in die Zukunft). News fliessen nicht ein, weil es keine News-Historie gibt."""
    umfeld = signale.makro_umfeld(df)
    ergebnisse = {}
    for name, a in config.ASSETS.items():
        p = df[name].dropna()
        tk = signale.trend_komponenten(p)
        makro = signale.makro_fuer_asset(umfeld, a["klasse"]).reindex(p.index).ffill()
        score = signale.kombiniere(tk["trend"], makro).dropna()
        if len(score) < 250:
            continue
        p = p.loc[score.index]
        rendite = p.pct_change().fillna(0)
        position = (score > 0).astype(float).shift(1).fillna(0)
        wechsel = position.diff().abs().fillna(0)
        strategie = position * rendite - wechsel * KOSTEN

        tpj = 365 if a["klasse"] == "krypto" else 252
        kurve_s, kurve_bh = (1 + strategie).cumprod(), (1 + rendite).cumprod()

        # Trefferquote: stimmt die Richtung klarer Signale in den nächsten N Tagen?
        zukunft = p.shift(-config.PRUEF_HORIZONT_TAGE) / p - 1
        klar = score[(score.abs() >= config.SCHWELLEN["normal"])].index
        paare = pd.DataFrame({"s": score.loc[klar], "z": zukunft.loc[klar]}).dropna()
        treffer = float((np.sign(paare["s"]) == np.sign(paare["z"])).mean()) if len(paare) else None
        basis = float((zukunft.dropna() > 0).mean())  # wie oft stieg der Kurs sowieso?

        ergebnisse[name] = {
            "zeitraum": f"{p.index[0]:%m.%Y}–{p.index[-1]:%m.%Y}",
            "cagr_strategie": _cagr(kurve_s, tpj), "cagr_halten": _cagr(kurve_bh, tpj),
            "maxdd_strategie": _max_drawdown(kurve_s), "maxdd_halten": _max_drawdown(kurve_bh),
            "trefferquote": treffer, "basisquote_steigt": basis,
            "wechsel_pro_jahr": float(wechsel.sum() / (len(p) / tpj)),
            "investiert_anteil": float(position.mean()),
        }
    return ergebnisse


# ------------------------------------------------------------------ Live-Protokoll

def protokolliere(pfad: Path, signale_heute: list[dict], datum: str) -> list[dict]:
    log = json.loads(pfad.read_text()) if pfad.exists() else []
    log = [e for e in log if e["datum"] != datum]  # mehrere Läufe pro Tag: letzter zählt
    log += [{"datum": datum, "name": s["name"], "score": s["score"], "kurs": s["kurs"]} for s in signale_heute]
    pfad.write_text(json.dumps(log, ensure_ascii=False, indent=0))
    return log


def live_trefferquote(log: list[dict], df: pd.DataFrame) -> dict:
    """Prüft alte Signale gegen den tatsächlichen Kursverlauf."""
    h, schwelle = config.PRUEF_HORIZONT_TAGE, config.SCHWELLEN["normal"]
    pro_asset: dict[str, list[bool]] = {}
    for e in log:
        if abs(e["score"]) < schwelle or e["name"] not in df:
            continue
        p = df[e["name"]].dropna()
        pos = p.index.searchsorted(pd.Timestamp(e["datum"]))
        if pos + h >= len(p):
            continue  # noch zu jung
        rendite = p.iloc[pos + h] / e["kurs"] - 1
        pro_asset.setdefault(e["name"], []).append(np.sign(rendite) == np.sign(e["score"]))
    alle = [t for v in pro_asset.values() for t in v]
    return {
        "geprueft": len(alle),
        "quote": float(np.mean(alle)) if alle else None,
        "pro_asset": {k: {"n": len(v), "quote": float(np.mean(v))} for k, v in pro_asset.items()},
        "erstes_signal": min((e["datum"] for e in log), default=None),
    }
