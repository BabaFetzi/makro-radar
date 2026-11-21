"""Erzeugt das Dashboard als einzelne HTML-Datei (fürs iPhone optimiert, als Web-App installierbar)."""
from __future__ import annotations

import json
from html import escape

FARBEN = {"Stark positiv": "#22c55e", "Positiv": "#86efac", "Neutral": "#94a3b8",
          "Negativ": "#fca5a5", "Stark negativ": "#ef4444"}


def _kurs(name: str, wert: float) -> str:
    if "/" in name:
        return f"{wert:.4f}" if wert < 10 else f"{wert:.2f}"
    return f"{wert:,.0f}".replace(",", "'") if wert >= 1000 else f"{wert:.2f}"


def _pct(x, stellen=1):
    return "–" if x is None else f"{x * 100:+.{stellen}f}%"


def _sparkline(werte: list[float], farbe: str) -> str:
    if len(werte) < 2:
        return ""
    lo, hi = min(werte), max(werte)
    spanne = (hi - lo) or 1
    pkt = " ".join(f"{i * 100 / (len(werte) - 1):.1f},{28 - (v - lo) / spanne * 26:.1f}" for i, v in enumerate(werte))
    return (f'<svg viewBox="0 0 100 30" preserveAspectRatio="none" class="spark">'
            f'<polyline points="{pkt}" fill="none" stroke="{farbe}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>')


def _balken(wert: int) -> str:
    """Horizontaler Balken von −100 bis +100 mit Mitte bei 0."""
    w = max(-100, min(100, wert))
    links = 50 if w >= 0 else 50 + w / 2
    farbe = "#22c55e" if w > 0 else "#ef4444"
    return (f'<div class="bar"><div class="mitte"></div>'
            f'<div class="fill" style="left:{links}%;width:{abs(w) / 2}%;background:{farbe}"></div></div>')


def _auto_lage(signale, umfeld) -> str:
    stark = sorted(signale, key=lambda s: -abs(s["score"]))[:3]
    teile = [f"Das Umfeld ist <b>{umfeld['regime']}</b> (VIX {umfeld['vix']})."]
    if umfeld["zinskurve"] < 0:
        teile.append("Die US-Zinskurve ist invertiert, historisch ein Warnsignal für eine Rezession.")
    teile.append("Deutlichste Signale: " + ", ".join(f"{s['name']} ({s['score']:+d})" for s in stark) + ".")
    return " ".join(teile)


def erzeuge(signale, umfeld, fred, news_analyse, backtest, live, erstellt, demo=False) -> str:
    gruppen = list(dict.fromkeys(s["gruppe"] for s in signale))
    lage = escape(news_analyse.get("lage") or "") or _auto_lage(signale, umfeld)
    regime_farbe = {"Risk-on": "#22c55e", "Risk-off": "#ef4444"}.get(umfeld["regime"], "#eab308")

    # Makro-Kacheln
    kacheln = [
        ("VIX (Angst)", f"{umfeld['vix']}", "hoch = Stress" if umfeld["vix"] > 20 else "ruhig"),
        ("Zinskurve 10J–3M", f"{umfeld['zinskurve']:+.2f}%", "invertiert" if umfeld["zinskurve"] < 0 else "normal"),
        ("US-Rendite 10J", f"{umfeld['us10j']:.2f}%", ""),
        ("Dollar-Trend", f"{umfeld['dollar_trend']:+d}", "stärker" if umfeld["dollar_trend"] > 10 else
         "schwächer" if umfeld["dollar_trend"] < -10 else "seitwärts"),
    ] + [(n, f"{v['wert']}%", f"vorher {v['vorher']}%" if v["vorher"] is not None else "") for n, v in fred.items()]
    kachel_html = "".join(f'<div class="kachel"><span>{escape(t)}</span><b>{escape(w)}</b><small>{escape(h)}</small></div>'
                          for t, w, h in kacheln)

    # Anlage-Karten
    karten = ""
    for s in signale:
        farbe = FARBEN[s["label"]]
        linie = "#22c55e" if s["verlauf"][-1] >= s["verlauf"][0] else "#ef4444"
        k = s["komponenten"]
        news_html = "".join(f'<li><span class="{"plus" if n["richtung"] > 0 else "minus"}">'
                            f'{"▲" if n["richtung"] > 0 else "▼"}</span> {escape(n["titel"])}</li>' for n in s["news_top"])
        karten += f"""
<details class="karte" data-gruppe="{escape(s['gruppe'])}">
 <summary>
  <div class="zeile1"><b>{escape(s['name'])}</b><span class="score" style="color:{farbe}">{s['score']:+d}</span></div>
  <div class="zeile2"><span>{_kurs(s['name'], s['kurs'])} <i class="{'plus' if s['veraenderung_1t'] >= 0 else 'minus'}">{_pct(s['veraenderung_1t'], 2)}</i></span>
   <span class="label" style="background:{farbe}22;color:{farbe}">{s['label']}</span></div>
  {_sparkline(s['verlauf'], linie)}
  {_balken(s['score'])}
 </summary>
 <div class="detail">
  <div class="komp"><span>Trend</span>{_balken(k['trend'])}<em>{k['trend']:+d}</em></div>
  <div class="komp"><span>Makro</span>{_balken(k['makro'])}<em>{k['makro']:+d}</em></div>
  <div class="komp"><span>News</span>{_balken(k['news'])}<em>{k['news']:+d}</em></div>
  <p class="meta">Konfidenz: <b>{s['konfidenz']}</b> · 1 Monat: {_pct(s['veraenderung_1m'])} · Volatilität: {s['vola'] * 100:.0f}% p.a.</p>
  <ul class="gruende">{''.join(f'<li>{escape(g)}</li>' for g in s['gruende'])}</ul>
  {f'<p class="meta">Wichtigste Meldungen:</p><ul class="news">{news_html}</ul>' if news_html else ''}
 </div>
</details>"""

    # Nachrichten
    news_liste = sorted(news_analyse["meldungen"], key=lambda m: -sum(abs(v) for v in m["wirkung"].values()))[:12]
    news_html = ""
    for m in news_liste:
        chips = "".join(f'<span class="chip {"plus" if v > 0 else "minus"}">{escape(a)} {"▲" * v if v > 0 else "▼" * -v}</span>'
                        for a, v in sorted(m["wirkung"].items(), key=lambda x: -abs(x[1])))
        titel = escape(m["titel"])
        if m.get("link"):
            titel = f'<a href="{escape(m["link"])}" target="_blank" rel="noopener">{titel}</a>'
        news_html += (f'<div class="meldung"><p>{titel}</p><small>{escape(m["quelle"])} · {escape(m["begruendung"])}</small>'
                      f'<div class="chips">{chips}</div></div>')
    if not news_html:
        news_html = '<p class="meta">Keine marktrelevanten Meldungen gefunden.</p>'

    # Prüfung
    bt_zeilen = ""
    for name, b in backtest.items():
        tq = b["trefferquote"]
        besser = tq is not None and tq > max(b["basisquote_steigt"], 1 - b["basisquote_steigt"])
        bt_zeilen += (f"<tr><td>{escape(name)}</td>"
                      f"<td class='{'plus' if besser else ''}'>{_pct(tq, 0) if tq is None else f'{tq * 100:.0f}%'}</td>"
                      f"<td>{b['basisquote_steigt'] * 100:.0f}%</td>"
                      f"<td>{_pct(b['cagr_strategie'], 0)} / {_pct(b['cagr_halten'], 0)}</td>"
                      f"<td>{b['maxdd_strategie'] * 100:.0f}% / {b['maxdd_halten'] * 100:.0f}%</td></tr>")
    zeitraum = next(iter(backtest.values()))["zeitraum"] if backtest else ""
    if live["quote"] is not None:
        live_text = (f"<b>{live['quote'] * 100:.0f}%</b> von {live['geprueft']} klaren Signalen lagen nach "
                     f"20 Handelstagen richtig (seit {live['erstes_signal']}).")
    else:
        live_text = (f"Noch keine Auswertung. Signale werden seit {live['erstes_signal'] or 'heute'} protokolliert "
                     "und nach 20 Handelstagen automatisch überprüft.")

    demo_hinweis = ('<div class="demo">DEMO-MODUS: künstliche Kurse und Beispiel-Nachrichten, '
                    'keine echten Marktdaten.</div>') if demo else ""
    filter_knoepfe = "".join(f'<button data-f="{escape(g)}">{escape(g)}</button>' for g in gruppen)

    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Makro-Radar">
<meta name="theme-color" content="#0b1120">
<link rel="apple-touch-icon" href="icon.png">
<title>Makro-Radar</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#0b1120;color:#e2e8f0;font-family:-apple-system,system-ui,sans-serif;line-height:1.4;-webkit-font-smoothing:antialiased}}
main{{max-width:720px;margin:auto;padding:calc(env(safe-area-inset-top) + 12px) 14px 40px}}
h1{{font-size:1.6rem;margin:4px 0}}h2{{font-size:1.05rem;margin:26px 0 8px;color:#cbd5e1}}
.kopf small{{color:#64748b}}.regime{{display:inline-block;padding:3px 10px;border-radius:20px;font-weight:600;font-size:.85rem;background:{regime_farbe}22;color:{regime_farbe}}}
.lage{{background:#111a2e;border:1px solid #1e293b;border-radius:14px;padding:12px 14px;font-size:.92rem;margin-top:10px}}
.kacheln{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}}
.kachel{{background:#111a2e;border-radius:12px;padding:10px}}.kachel span{{font-size:.72rem;color:#94a3b8;display:block}}
.kachel b{{font-size:1.25rem;display:block}}.kachel small{{color:#64748b;font-size:.72rem}}
.filter{{display:flex;gap:6px;overflow-x:auto;padding-bottom:4px;margin-bottom:8px}}
.filter button{{background:#111a2e;color:#cbd5e1;border:1px solid #1e293b;border-radius:20px;padding:6px 12px;font-size:.82rem;white-space:nowrap}}
.filter button.aktiv{{background:#2563eb;border-color:#2563eb;color:#fff}}
.karte{{background:#111a2e;border:1px solid #1e293b;border-radius:14px;padding:12px 14px;margin-bottom:8px}}
.karte summary{{list-style:none;cursor:pointer}}.karte summary::-webkit-details-marker{{display:none}}
.zeile1,.zeile2{{display:flex;justify-content:space-between;align-items:center}}.zeile1 b{{font-size:1.02rem}}
.score{{font-size:1.4rem;font-weight:700;font-variant-numeric:tabular-nums}}
.zeile2{{font-size:.85rem;color:#94a3b8;margin-top:2px}}.zeile2 i{{font-style:normal;margin-left:4px}}
.label{{font-size:.72rem;padding:2px 8px;border-radius:20px;font-weight:600}}
.spark{{width:100%;height:34px;margin:6px 0 4px;display:block}}
.bar{{position:relative;height:6px;background:#1e293b;border-radius:3px;flex:1}}.bar .mitte{{position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:#475569}}
.bar .fill{{position:absolute;top:0;bottom:0;border-radius:3px}}
.detail{{margin-top:10px;border-top:1px solid #1e293b;padding-top:10px}}
.komp{{display:flex;align-items:center;gap:8px;font-size:.8rem;margin:5px 0}}.komp span{{width:48px;color:#94a3b8}}.komp em{{width:34px;text-align:right;font-style:normal;font-variant-numeric:tabular-nums}}
.meta{{font-size:.78rem;color:#94a3b8;margin:8px 0 4px}}
.gruende,.news{{margin:4px 0;padding-left:18px;font-size:.84rem}}.gruende li,.news li{{margin:3px 0}}.news{{list-style:none;padding-left:0}}
.plus{{color:#22c55e}}.minus{{color:#ef4444}}
.meldung{{background:#111a2e;border-radius:12px;padding:10px 12px;margin-bottom:7px}}.meldung p{{margin:0 0 3px;font-size:.88rem}}
.meldung a{{color:#e2e8f0;text-decoration:none}}.meldung small{{color:#64748b;font-size:.74rem}}
.chips{{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}}.chip{{font-size:.7rem;background:#1e293b;border-radius:6px;padding:2px 6px}}
table{{width:100%;border-collapse:collapse;font-size:.76rem}}th,td{{padding:6px 4px;text-align:right;border-bottom:1px solid #1e293b}}
th:first-child,td:first-child{{text-align:left}}th{{color:#94a3b8;font-weight:500}}
.box{{background:#111a2e;border-radius:12px;padding:12px;overflow-x:auto}}
.demo{{background:#7c2d12;color:#fed7aa;border-radius:10px;padding:8px 12px;font-size:.82rem;margin-bottom:10px}}
footer{{color:#475569;font-size:.72rem;margin-top:28px;text-align:center}}
</style></head><body><main>
{demo_hinweis}
<div class="kopf"><small>Stand {escape(erstellt)} · Kurse vom {umfeld['datum']}</small>
<h1>Makro-Radar</h1><span class="regime">{umfeld['regime']} · Risiko-Index {umfeld['risiko']:+d}</span></div>
<div class="lage">{lage}</div>

<h2>Makro-Indikatoren</h2><div class="kacheln">{kachel_html}</div>

<h2>Signale</h2>
<div class="filter"><button class="aktiv" data-f="">Alle</button>{filter_knoepfe}</div>
{karten}

<h2>Nachrichten mit Marktwirkung</h2>
<p class="meta">Auswertung: {escape(news_analyse['modus'])} · {len(news_analyse['meldungen'])} relevante Meldungen</p>
{news_html}

<h2>Wie gut sind die Signale?</h2>
<div class="box"><p class="meta" style="margin-top:0">Live-Prüfung: {live_text}</p>
<p class="meta">Backtest {escape(zeitraum)} (nur Trend + Makro, News haben keine Historie). Treffer = Richtung nach 20 Tagen richtig. Basis = wie oft der Kurs ohnehin stieg. Grün = besser als blind raten.</p>
<table><tr><th>Anlage</th><th>Treffer</th><th>Basis</th><th>Rendite p.a.<br>Signal / Halten</th><th>Max. Verlust<br>Signal / Halten</th></tr>{bt_zeilen}</table></div>

<footer>Automatische Analyse, keine Anlageberatung. Signale sind Entscheidungshilfen, keine Garantie.<br>Daten: Yahoo Finance{', FRED' if fred else ''}, öffentliche RSS-Feeds.</footer>
</main>
<script>
document.querySelectorAll('.filter button').forEach(b=>b.onclick=()=>{{
 document.querySelectorAll('.filter button').forEach(x=>x.classList.toggle('aktiv',x===b));
 document.querySelectorAll('.karte').forEach(k=>k.style.display=(!b.dataset.f||k.dataset.gruppe===b.dataset.f)?'':'none');
}});
</script>
<script type="application/json" id="daten">{json.dumps({"signale": [{k: v for k, v in s.items() if k != "verlauf"} for s in signale], "umfeld": umfeld}, ensure_ascii=False).replace("</", "<\\/")}</script>
</body></html>"""
