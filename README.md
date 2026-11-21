# Makro-Radar

Beobachtet das Weltgeschehen und die Märkte wie ein Global-Macro-Investor und zeigt die Ergebnisse als App auf dem iPhone.

**Märkte:** SMI, S&P 500, DAX, Nasdaq · EUR/CHF, USD/CHF, EUR/USD, USD/JPY · Gold, Öl, Kupfer · Bitcoin, Ethereum

## Wie ein Signal entsteht

| Baustein | Gewicht | Was er misst |
|---|---|---|
| **Trend** | 45 % | Abstand zum 200-Tage-Schnitt, 50/200-Kreuz, Momentum über 3 und 12 Monate (im Verhältnis zur Schwankung) |
| **Makro** | 25 % | Risk-on/Risk-off aus VIX (Niveau + Richtung) und US-Zinskurve, dazu der Dollar-Trend. Jede Anlageklasse reagiert anders (Franken, Yen und Gold sind sichere Häfen) |
| **News** | 30 % | Schlagzeilen von Fed, EZB, CNBC, MarketWatch, CoinDesk und Google News. Neue Meldungen zählen mehr (Halbwertszeit 24 h) |

Das Ergebnis ist ein Score von −100 bis +100 mit Begründung und Konfidenz. Die Konfidenz ist hoch, wenn alle Bausteine in dieselbe Richtung zeigen.

**News-Auswertung umschaltbar:**
- Mit `ANTHROPIC_API_KEY` liest Claude die Schlagzeilen, versteht Zusammenhänge und schreibt eine Lage-Zusammenfassung. Kosten: ca. 1–5 CHF pro Monat.
- Ohne Key greift eine Auswertung per Schlüsselwörter (rund 20 Regeln). Sie ist gratis, aber gröber.
- Erzwingen lässt sich ein Modus mit `--news claude` oder `--news keywords`, in GitHub über die Variable `NEWS_MODUS`.

## Wie ehrlich sind die Signale?

Das Dashboard zeigt zwei Prüfungen:

1. **Backtest:** Die Trend- und Makro-Logik wird auf ca. 5 Jahre Historie angewendet. Das Signal von heute wirkt erst ab morgen, also ohne Blick in die Zukunft, und es werden 0,1 % Kosten pro Wechsel abgezogen. Die Trefferquote steht neben der Basisquote („wie oft stieg der Kurs sowieso?“), denn erst wenn die Trefferquote höher ist, bringt das Signal etwas.
2. **Live-Prüfung:** Jedes Signal wird in `daten/signal_log.json` gespeichert und nach 20 Handelstagen automatisch mit dem echten Kursverlauf verglichen. Das ist die einzige Prüfung, die auch die News mitbewertet.

## Einrichtung (einmalig, ca. 15 Minuten)

1. **GitHub-Konto** erstellen (gratis) und ein neues **öffentliches** Repository `makro-radar` anlegen. GitHub Pages ist nur bei öffentlichen Repos gratis.
2. Alle Dateien aus diesem Ordner hochladen (inkl. des versteckten Ordners `.github`).
3. **Settings → Pages → Source: „GitHub Actions“** wählen.
4. Optional unter **Settings → Secrets and variables → Actions → New repository secret**:
   - `ANTHROPIC_API_KEY`: für die Claude-Auswertung (console.anthropic.com)
   - `FRED_API_KEY`: für Inflation, Arbeitslosigkeit und Leitzins der USA (gratis auf fred.stlouisfed.org)
5. **Actions → „Makro-Radar aktualisieren“ → Run workflow** für den ersten Lauf. Danach läuft es automatisch um 07:15 und 22:45 Uhr (Schweizer Winterzeit).
6. Die Adresse `https://DEINNAME.github.io/makro-radar/` in Safari öffnen, dann **Teilen → Zum Home-Bildschirm**.

## Lokal ausführen

```bash
pip install -r requirements.txt
python main.py --demo      # ohne Internet, künstliche Daten
python main.py             # echte Daten
python -m unittest -v      # Tests
```
Das Dashboard liegt danach in `docs/index.html`.

## Anpassen

Alles Wichtige steht in `config.py`: Märkte (Yahoo-Ticker), Gewichtung, Schwellen, Nachrichtenquellen und das Claude-Modell.

## Aufbau

```
main.py        Ablauf
config.py      Einstellungen
daten.py       Kurse (Yahoo Finance), FRED, Demo-Daten
news.py        RSS-Feeds holen, Auswertung per Claude oder Schlüsselwörter
signale.py     Trend, Makro-Umfeld, Gesamtscore
pruefung.py    Backtest und Live-Trefferquote
dashboard.py   HTML fürs iPhone
.github/workflows/update.yml   Automatik in der Cloud
```

## Grenzen

- Kein Modell sagt Märkte zuverlässig voraus. Die Signale sind eine Entscheidungshilfe und keine Anlageberatung.
- Yahoo Finance ist eine inoffizielle, kostenlose Quelle und kann gelegentlich ausfallen oder Lücken haben.
- Schlagzeilen sind nicht ganze Artikel. Ironie, Dementis oder bereits „eingepreiste“ Nachrichten erkennt auch Claude nicht immer.
- Der Backtest prüft nur Trend und Makro. Wie gut die News helfen, zeigt erst die Live-Prüfung nach einigen Wochen.
