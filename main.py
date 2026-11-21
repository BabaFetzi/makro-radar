"""Makro-Radar: holt Daten, wertet aus und schreibt das Dashboard nach docs/index.html.

    python main.py                 # echte Daten (Claude, wenn ANTHROPIC_API_KEY gesetzt ist)
    python main.py --news keywords # News nur per Schlüsselwörter
    python main.py --demo          # ohne Internet, künstliche Daten zum Testen
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import aktien
import aktien_seite
import daten
import dashboard
import news
import pruefung
import signale

BASIS = Path(__file__).parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="künstliche Daten, kein Internet nötig")
    ap.add_argument("--news", choices=["auto", "claude", "keywords"], default="auto")
    ap.add_argument("--out", type=Path, default=BASIS / "docs" / "index.html")
    args = ap.parse_args()

    print("1/5 Kurse laden …")
    df = daten.demo_kurse() if args.demo else daten.lade_kurse()
    fred = {} if args.demo else daten.lade_fred()

    print("2/5 Nachrichten laden und auswerten …")
    meldungen = daten.demo_news() if args.demo else news.hole_news()
    analyse = news.analysiere(meldungen, args.news)
    print(f"     {len(meldungen)} Meldungen, {len(analyse['meldungen'])} relevant ({analyse['modus']})")

    print("3/5 Signale berechnen …")
    aktuelle, umfeld = signale.aktuelle_signale(df, news.news_scores(analyse))

    print("4/5 Backtest und Live-Prüfung …")
    bt = pruefung.backtest(df)
    log_pfad = BASIS / "daten" / ("signal_log_demo.json" if args.demo else "signal_log.json")
    log_pfad.parent.mkdir(exist_ok=True)
    log = pruefung.protokolliere(log_pfad, aktuelle, umfeld["datum"])
    live = pruefung.live_trefferquote(log, df)

    print("5/5 Dashboard schreiben …")
    erstellt = datetime.now(ZoneInfo("Europe/Zurich")).strftime("%d.%m.%Y %H:%M")
    html = dashboard.erzeuge(aktuelle, umfeld, fred, analyse, bt, live, erstellt, demo=args.demo)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    (args.out.parent / "daten.json").write_text(json.dumps(
        {"erstellt": erstellt, "umfeld": umfeld, "signale": aktuelle, "fred": fred,
         "news": analyse, "backtest": bt, "live": live}, ensure_ascii=False, default=str), encoding="utf-8")

    print("6/6 Aktien-Empfehlungen …")
    try:
        if args.demo:
            kurse_aktien, fund = daten.demo_aktien(df.index)
        else:
            kurse_aktien = aktien.lade_kurse()
            fund = aktien.lade_fundamentaldaten(BASIS / "daten" / "fundamentaldaten.json")
        liste, lage = aktien.rangliste(kurse_aktien, fund, df)
        seite = aktien_seite.erzeuge(liste, lage, aktien.markt_ampel(df, umfeld),
                                     aktien.backtest(kurse_aktien, df), erstellt, demo=args.demo)
        (args.out.parent / "aktien.html").write_text(seite, encoding="utf-8")
        print("     Top 5: " + ", ".join(f"{e['name']} ({e['score']})" for e in liste if e["gruppe"] != "ETFs")[:200])
    except Exception as e:  # Aktien-Teil darf den Makro-Radar nicht blockieren
        print(f"     Aktien-Empfehlungen fehlgeschlagen: {e}")

    print(f"\nUmfeld: {umfeld['regime']} (VIX {umfeld['vix']})")
    for s in sorted(aktuelle, key=lambda s: -s["score"]):
        print(f"  {s['name']:<10} {s['score']:+4d}  {s['label']:<13} Konfidenz {s['konfidenz']}")
    print(f"\nDashboard: {args.out.resolve()}")


if __name__ == "__main__":
    main()
