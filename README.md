# Weekend Deal Scanner - Setup Guide

## Was macht das Script?

1. Scannt alle Wizz Air Ziele ab Bukarest (OTP)
2. Sucht Flüge für Fr-So (nächste 4 Wochen)
3. Sucht 4★+ Hotels unter €50/Nacht
4. Filtert: Flight + Hotel < €100 ODER "Banger Deal" (z.B. 5★ Hotel für €40)
5. Schickt dir Report per Telegram

---

## SETUP IN 10 MINUTEN

### Schritt 1: Telegram Bot erstellen (2 min)

1. Öffne Telegram, suche "@BotFather"
2. Schreibe `/newbot`
3. Gib einen Namen ein (z.B. "Havok Deal Scanner")
4. Gib einen Username ein (z.B. "havok_deals_bot")
5. Du bekommst einen **API Token** - KOPIEREN!

Beispiel Token: `6123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxx`

### Schritt 2: Deine Chat ID finden (1 min)

1. Starte deinen neuen Bot (klick auf den Link von BotFather)
2. Schreibe ihm irgendwas (z.B. "hi")
3. Öffne im Browser: `https://api.telegram.org/bot<DEIN_TOKEN>/getUpdates`
4. Suche nach `"chat":{"id":` - das ist deine **Chat ID**

Beispiel Chat ID: `123456789`

### Schritt 3: Kiwi.com API Key (3 min) - GRATIS

1. Gehe zu: https://tequila.kiwi.com/
2. Registriere dich (kostenlos)
3. Erstelle eine "Solution" (App)
4. Kopiere deinen **API Key**

### Schritt 4: Online Hosting (kostenlos)

**Option A: Railway.app (empfohlen)**
1. Gehe zu https://railway.app
2. Login mit GitHub
3. "New Project" → "Deploy from GitHub repo"
4. Lade die Files hoch oder verbinde dein Repo
5. Unter "Variables" füge hinzu:
   - `TELEGRAM_BOT_TOKEN` = dein Bot Token
   - `TELEGRAM_CHAT_ID` = deine Chat ID
   - `KIWI_API_KEY` = dein Kiwi API Key

**Option B: GitHub Actions (100% gratis)**
Siehe `github_action.yml` unten

---

## ENVIRONMENT VARIABLES

```bash
TELEGRAM_BOT_TOKEN=6123456789:AAHxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789
KIWI_API_KEY=your_kiwi_api_key_here
```

---

## LOKAL TESTEN

```bash
# 1. Clone / Download
cd weekend_deal_scanner

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# 3. Dependencies
pip install -r requirements.txt

# 4. Environment variables setzen
export TELEGRAM_BOT_TOKEN="dein_token"
export TELEGRAM_CHAT_ID="deine_id"
export KIWI_API_KEY="dein_key"

# 5. Ausführen
python scanner.py
```

---

## AUTOMATISCH JEDEN TAG LAUFEN LASSEN

### GitHub Actions (GRATIS, empfohlen)

Erstelle `.github/workflows/scan.yml`:

```yaml
name: Weekend Deal Scanner

on:
  schedule:
    # Jeden Tag um 8:00 UTC (10:00 Bukarest)
    - cron: '0 8 * * *'
  workflow_dispatch:  # Manual trigger

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run scanner
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          KIWI_API_KEY: ${{ secrets.KIWI_API_KEY }}
        run: python scanner.py
```

Dann in GitHub:
1. Gehe zu deinem Repo → Settings → Secrets and variables → Actions
2. Füge die 3 Secrets hinzu (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, KIWI_API_KEY)

---

## ANPASSEN

In `scanner.py` kannst du ändern:

```python
MAX_TOTAL_PRICE = 100      # Max Gesamtpreis
MAX_FLIGHT_PRICE = 60      # Max Flugpreis (roundtrip)
MAX_HOTEL_PRICE = 60       # Max Hotel/Nacht
MIN_HOTEL_RATING = 4.0     # Min Sterne
BANGER_HOTEL_THRESHOLD = 40  # "Banger" wenn 4★+ Hotel unter diesem Preis

# Destinations hinzufügen/entfernen
DESTINATIONS = [
    {"code": "SOF", "city": "Sofia", "country": "Bulgaria"},
    # ...
]
```

---

## BEISPIEL OUTPUT

```
🔥🔥🔥 BANGER DEAL

Sofia, Bulgaria

✈️ Flug:
Hin: Fri 13.12 18:30
Zurück: Sun 15.12 20:15
Preis: €38

🏨 Hotel:
Grand Hotel Sofia (4⭐)
Rating: 8.7/10
Preis: €35/Nacht

💰 TOTAL: €73

🔗 Hotel buchen
```

---

## TROUBLESHOOTING

**"No API keys configured"**
→ KIWI_API_KEY nicht gesetzt

**Keine Telegram Nachrichten**
→ Check Bot Token und Chat ID
→ Hast du den Bot gestartet? (erste Nachricht schicken)

**Zu wenige Ergebnisse**
→ MAX_TOTAL_PRICE erhöhen
→ MIN_HOTEL_RATING auf 3.5 senken

---

## KOSTEN

- Telegram Bot: GRATIS
- Kiwi.com API: GRATIS (fair use)
- GitHub Actions: GRATIS (2000 min/Monat)
- Railway.app: GRATIS tier verfügbar

**Total: €0**
