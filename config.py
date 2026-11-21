"""Zentrale Einstellungen für den Makro-Radar."""

# ------------------------------------------------------------------ Märkte
# klasse: bestimmt, wie das Makro-Umfeld (Risk-on / Risk-off) auf den Wert wirkt
ASSETS = {
    # Aktienindizes
    "SMI":        {"ticker": "^SSMI",    "klasse": "aktien",  "gruppe": "Aktienindizes"},
    "S&P 500":    {"ticker": "^GSPC",    "klasse": "aktien",  "gruppe": "Aktienindizes"},
    "DAX":        {"ticker": "^GDAXI",   "klasse": "aktien",  "gruppe": "Aktienindizes"},
    "Nasdaq":     {"ticker": "^IXIC",    "klasse": "aktien",  "gruppe": "Aktienindizes"},
    # Währungen (Kurs = wie viel von der 2. Währung für 1 Einheit der 1. Währung)
    "EUR/CHF":    {"ticker": "EURCHF=X", "klasse": "fx_gegen_chf", "gruppe": "Währungen"},
    "USD/CHF":    {"ticker": "USDCHF=X", "klasse": "fx_gegen_chf", "gruppe": "Währungen"},
    "EUR/USD":    {"ticker": "EURUSD=X", "klasse": "fx_gegen_usd", "gruppe": "Währungen"},
    "USD/JPY":    {"ticker": "USDJPY=X", "klasse": "fx_gegen_jpy", "gruppe": "Währungen"},
    # Rohstoffe & Gold
    "Gold":       {"ticker": "GC=F",     "klasse": "gold",    "gruppe": "Rohstoffe & Gold"},
    "Öl (WTI)":   {"ticker": "CL=F",     "klasse": "zyklisch_rohstoff", "gruppe": "Rohstoffe & Gold"},
    "Kupfer":     {"ticker": "HG=F",     "klasse": "zyklisch_rohstoff", "gruppe": "Rohstoffe & Gold"},
    # Krypto
    "Bitcoin":    {"ticker": "BTC-USD",  "klasse": "krypto",  "gruppe": "Krypto"},
    "Ethereum":   {"ticker": "ETH-USD",  "klasse": "krypto",  "gruppe": "Krypto"},
}

# Makro-Indikatoren (ebenfalls über Yahoo Finance, kein API-Key nötig)
INDIKATOREN = {
    "VIX":       "^VIX",      # "Angstindex" der US-Börse
    "US10J":     "^TNX",      # Rendite 10-jährige US-Staatsanleihe (in %)
    "US3M":      "^IRX",      # Rendite 3-monatige US-Staatsanleihe (in %)
    "DOLLAR":    "DX-Y.NYB",  # Dollar-Index gegen Währungskorb
}

# Optional: zusätzliche Daten der US-Notenbank (FRED), nur mit FRED_API_KEY
FRED_SERIEN = {
    "Inflation USA": "CPIAUCSL",   # wird in Veränderung zum Vorjahr umgerechnet
    "Arbeitslosigkeit USA": "UNRATE",
    "Leitzins USA": "FEDFUNDS",
}

# Wie stark reagiert eine Klasse auf Risk-on (+) / Risk-off (-)?
# +1: steigt bei Risk-on, -1: steigt bei Risk-off ("sicherer Hafen")
RISIKO_SENSITIVITAET = {
    "aktien": 1.0,
    "krypto": 1.0,
    "zyklisch_rohstoff": 0.7,
    "gold": -0.6,
    "fx_gegen_chf": 0.8,     # CHF ist sicherer Hafen -> EUR/CHF fällt bei Risk-off
    "fx_gegen_usd": 0.4,
    "fx_gegen_jpy": 0.8,     # JPY ist sicherer Hafen -> USD/JPY fällt bei Risk-off
}

# Wie reagiert eine Klasse auf einen steigenden Dollar?
DOLLAR_SENSITIVITAET = {
    "aktien": -0.2, "krypto": -0.5, "zyklisch_rohstoff": -0.5, "gold": -0.7,
    "fx_gegen_chf": 0.0, "fx_gegen_usd": -1.0, "fx_gegen_jpy": 0.5,
}

# ------------------------------------------------------------------ Gewichtung des Gesamtsignals
GEWICHTE = {"trend": 0.45, "makro": 0.25, "news": 0.30}

# Ab welchem Score (−100…+100) gilt ein Signal als positiv/negativ
SCHWELLEN = {"stark": 50, "normal": 20}

# Nach wie vielen Handelstagen ein Signal live überprüft wird
PRUEF_HORIZONT_TAGE = 20

# ------------------------------------------------------------------ Nachrichten
NEWS_FEEDS = {
    "Fed (US-Notenbank)": "https://www.federalreserve.gov/feeds/press_all.xml",
    "EZB": "https://www.ecb.europa.eu/rss/press.html",
    "CNBC Wirtschaft": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "CNBC Top News": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "MarketWatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Google News: Märkte": "https://news.google.com/rss/search?q=markets+inflation+central+bank+when:2d&hl=en-US&gl=US&ceid=US:en",
    "Google News: Geopolitik": "https://news.google.com/rss/search?q=geopolitics+OR+tariffs+OR+sanctions+OR+OPEC+when:2d&hl=en-US&gl=US&ceid=US:en",
    "Google News: Schweiz": "https://news.google.com/rss/search?q=SNB+OR+Franken+OR+SMI+when:3d&hl=de&gl=CH&ceid=CH:de",
}
NEWS_MAX_ALTER_STUNDEN = 48
NEWS_MAX_ANZAHL = 80

# Claude-Modell für die News-Auswertung (nur wenn ANTHROPIC_API_KEY gesetzt ist)
CLAUDE_MODELL = "claude-sonnet-5-5"
