"""HTML-Seite docs/aktien.html mit den Aktien-Empfehlungen."""
from __future__ import annotations

from html import escape

from dashboard import _sparkline

AMPEL = {"grün": "#22c55e", "gelb": "#eab308", "rot": "#ef4444"}


def _faktor(name: str, wert) -> str:
    if wert is None:
        return f'<span class="f leer">{name} –</span>'
    farbe = "#22c55e" if wert > 0.3 else "#ef4444" if wert < -0.3 else "#94a3b8"
    pfeil = "▲" if wert > 0.3 else "▼" if wert < -0.3 else "●"
    return f'<span class="f" style="color:{farbe}">{name} {pfeil}</span>'


def _karte(e: dict, rang: int | None = None) -> str:
    farbe = "#22c55e" if e["score"] >= 80 else "#86efac" if e["score"] >= 60 else "#94a3b8" if e["score"] >= 40 else "#ef4444"
    linie = "#22c55e" if e["verlauf"][-1] >= e["verlauf"][0] else "#ef4444"
    perf = "" if e["perf12"] is None else f'<i class="{"plus" if e["perf12"] >= 0 else "minus"}">{e["perf12"] * 100:+.0f}% 12M</i>'
    return f"""
<details class="karte" data-gruppe="{escape(e['gruppe'])}">
 <summary>
  <div class="zeile1"><b>{f'<span class="rang">{rang}</span>' if rang else ''}{escape(e['name'])}</b>
   <span class="score" style="color:{farbe}">{e['score']}</span></div>
  <div class="zeile2"><span>{escape(e['ticker'])} · {escape(e['sektor'])}</span>{perf}</div>
  <div class="faktoren">{_faktor('Momentum', e['momentum'])}{_faktor('Qualität', e['qualitaet'])}{_faktor('Makro', e['makro'])}</div>
 </summary>
 <div class="detail">{_sparkline(e['verlauf'], linie)}
  <ul>{''.join(f'<li>{escape(g)}</li>' for g in e['gruende'])}</ul>
  <p class="meta">Schwankung: {e['vola'] * 100:.0f}% pro Jahr · Score = Rang im Vergleich zu allen {{N}} Titeln (100 = bester)</p>
 </div>
</details>"""


def erzeuge(liste: list[dict], lage: dict, ampel: dict, bt: dict, erstellt: str, demo: bool = False) -> str:
    aktien = [e for e in liste if e["gruppe"] != "ETFs"]
    etfs = [e for e in liste if e["gruppe"] == "ETFs"]
    top = aktien[:10]
    pro_region = {g: [e for e in aktien if e["gruppe"] == g][:3] for g in ("Schweiz", "USA", "Europa")}
    schlusslicht = aktien[-5:][::-1]
    n = str(len(liste))

    top_html = "".join(_karte(e, i + 1) for i, e in enumerate(top))
    region_html = "".join(f"<h3>{escape(g)}</h3>" + "".join(_karte(e) for e in l) for g, l in pro_region.items())
    etf_html = "".join(_karte(e, i + 1) for i, e in enumerate(etfs))
    meiden_html = "".join(_karte(e) for e in schlusslicht)

    if bt:
        bt_html = (f"<p>Über {bt['monate']} Monate: Die monatlichen Top 10 (nur Momentum + Makro) erzielten "
                   f"<b>{bt['cagr_top'] * 100:+.1f}% pro Jahr</b>, alle Aktien gleich gewichtet <b>{bt['cagr_alle'] * 100:+.1f}%</b>. "
                   f"Die Top 10 waren in <b>{bt['monate_besser'] * 100:.0f}%</b> der Monate besser. "
                   f"Grösster Verlust: Top 10 {bt['maxdd_top'] * 100:.0f}%, alle {bt['maxdd_alle'] * 100:.0f}%.</p>"
                   "<p class='meta'>Vorsicht: Der Test nutzt die heutige Titelauswahl. Firmen, die in der Zeit abgestürzt "
                   "oder aus dem Index geflogen sind, fehlen, deshalb sieht die Vergangenheit etwas zu gut aus. "
                   "Kennzahlen (KGV usw.) gibt es nicht historisch und sind nicht getestet.</p>")
    else:
        bt_html = "<p class='meta'>Zu wenig Historie für einen Backtest.</p>"

    lage_txt = (f"Risiko {lage['risiko']:+.2f} · Zinstrend {lage['zinsen']:+.2f} · Öltrend {lage['oel']:+.2f}")
    demo_html = '<div class="demo">DEMO-MODUS: künstliche Daten.</div>' if demo else ""

    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="theme-color" content="#0b1120">
<link rel="apple-touch-icon" href="icon.png"><title>Aktien-Empfehlungen</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#0b1120;color:#e2e8f0;font-family:-apple-system,system-ui,sans-serif;line-height:1.4}}
main{{max-width:720px;margin:auto;padding:calc(env(safe-area-inset-top) + 12px) 14px 40px}}
a{{color:#60a5fa;text-decoration:none}}h1{{font-size:1.5rem;margin:6px 0}}h2{{font-size:1.05rem;margin:26px 0 8px;color:#cbd5e1}}
h3{{font-size:.9rem;color:#94a3b8;margin:14px 0 6px}}small,.meta{{color:#64748b;font-size:.78rem}}
.ampel{{border-radius:14px;padding:12px 14px;margin:12px 0;background:{AMPEL[ampel['farbe']]}1a;border:1px solid {AMPEL[ampel['farbe']]}55}}
.ampel b{{color:{AMPEL[ampel['farbe']]}}}
.karte{{background:#111a2e;border:1px solid #1e293b;border-radius:14px;padding:11px 14px;margin-bottom:7px}}
.karte summary{{list-style:none;cursor:pointer}}.karte summary::-webkit-details-marker{{display:none}}
.zeile1,.zeile2{{display:flex;justify-content:space-between;align-items:center}}
.zeile2{{font-size:.8rem;color:#94a3b8}}.zeile2 i{{font-style:normal}}
.rang{{display:inline-block;min-width:22px;color:#64748b;font-weight:500}}
.score{{font-size:1.3rem;font-weight:700}}.faktoren{{display:flex;gap:10px;margin-top:6px;font-size:.75rem}}.f.leer{{color:#475569}}
.detail{{border-top:1px solid #1e293b;margin-top:8px;padding-top:6px}}.detail ul{{margin:6px 0;padding-left:18px;font-size:.84rem}}
.spark{{width:100%;height:34px;display:block}}.plus{{color:#22c55e}}.minus{{color:#ef4444}}
.box{{background:#111a2e;border-radius:12px;padding:12px;font-size:.88rem}}
.demo{{background:#7c2d12;color:#fed7aa;border-radius:10px;padding:8px 12px;font-size:.82rem}}
footer{{color:#475569;font-size:.72rem;margin-top:28px;text-align:center}}
</style></head><body><main>
{demo_html}
<a href="index.html">‹ Makro-Radar</a>
<h1>Aktien-Empfehlungen</h1><small>Stand {escape(erstellt)} · {n} Titel geprüft · {lage_txt}</small>
<div class="ampel"><b>Markt-Ampel: {ampel['farbe'].capitalize()}</b><br>{escape(ampel['text'])}</div>

<h2>Top 10 Einzelaktien</h2>
<p class="meta">Score = Rang aus Momentum (40%), Qualität & Bewertung (35%) und Makro-Sektor-Fit (25%). Antippen für Details.</p>
{top_html}

<h2>Beste pro Region</h2>{region_html}

<h2>ETFs (breiter gestreut)</h2>
<p class="meta">US-Sektor-ETFs als Signal, welche Branchen vorne liegen. In der Schweiz gibt es vergleichbare UCITS-ETFs (z.B. von iShares, Xtrackers, UBS).</p>
{etf_html}

<h2>Schlusslicht (eher meiden)</h2>{meiden_html}

<h2>Hätte das früher funktioniert?</h2><div class="box">{bt_html}</div>

<footer>Automatische Rangliste, keine Anlageberatung. Ersetzt nicht die eigene Prüfung des Unternehmens.<br>
Grundregeln: breit streuen, nur Geld investieren, das man mehrere Jahre nicht braucht, Notreserve vorher aufbauen.</footer>
</main></body></html>""".replace("{N}", n)
