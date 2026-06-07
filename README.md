# DXSpot

Monitor d'entitats DXCC en temps real via DX Cluster + Club Log | *Real-time DXCC entity monitor via DX Cluster + Club Log*

---

## 📖 CAT — Català

Monitoritza spots en temps real des d'un DX Cluster, compara'ls amb el teu DXCC Chart de Club Log i t'avisa per Telegram de noves entitats DXCC.

### Funcionalitats

- **Monitor en temps real** — connexió Telnet persistent al teu DX Cluster preferit
- **Integració Club Log (lifetime)** — baixa el teu DXCC Chart per saber quines entitats has treballat mai
- **Integració Club Log (any actual)** — baixa el chart de l'any en curs (`date=3`) per saber quines entitats has treballat aquest any
- **Sense dependències ADIF/eQSL** — no cal descarregar ADIF, no cal eQSL
- **Detecció de mode** — detecta automàticament FT8, FT4, CW, SSB, RTTY, amb fallback per freqüència
- **Alertes Telegram** — notificacions configurables amb dos nivells:
  - 🚨 **Mai treballada** (24/7)
  - 🌅 **NO treballada l'any en curs** (només en horari diürn)
- **Alertes Telegram** — tres nivells:
  - 🚨 **Mai treballada** (24/7)
  - 🌅 **NO treballada l'any en curs** (horari diürn)
  - 💤 **NO confirmada l'any en curs** (horari diürn, només amb )
- **** — flag opcional per activar alertes d'entitats treballades però encara no confirmades
- **Confirmades l'any en curs** — completament silenciades
- **Deduplicació** — control de re-alertes amb interval configurable (2h per defecte)
- **QSY detection** — si el mateix prefix apareix a una freqüència diferent, re-alerta amb "QSY! era X kHz"
- **Silenci nocturn configurable** — les entitats ja treballades (però no aquest any) només alerten de dia
- **Actualització automàtica** — els mapes de prefixos i els charts de Club Log es refresquen cada 24h
- **Llista d'entitats mai treballades** — manté un set actualitzat per saber què falta

### Requisits

- Python 3.8+
- `requests` — llibreria HTTP
- `parse_cty.py` — genera `dxcc_prefixes.json` des del `cty.dat` de l'ARRL
- Connexió a internet (DX Cluster, Club Log API)

### Instal·lació

```bash
# Clonar el repositori
git clone https://github.com/TecnoTalarn/DXSpot.git
cd DXSpot

# Instal·lar dependències
pip install requests

# Generar mapa de prefixos
python3 parse_cty.py        # genera dxcc_prefixes.json

# Configuració inicial
python3 dxcc_clublog_v4.py \
    --callsign TEUCALL \
    --clublog-api-key TEU_CLUBLOG_API_KEY \
    --clublog-email TEU_EMAIL \
    --clublog-password TEU_PASSWORD \
    --telegram-token 123456:ABC \
    --telegram-chat-id 987654
```

### Arguments

| Argument | Curt | Per defecte | Descripció |
|----------|------|-------------|------------|
| `--callsign` | | **obligatori** | El teu indicatiu |
| `--cluster-login` | | = callsign | Indicatiu pel login al cluster (si és diferent) |
| `--year` | `-y` | any actual | Any per filtrar chart i alertes |
| `--modes` | `-m` | `ALL` | Modes separats per coma (FT8,SSB,FT4...) o ALL |
| `--freq-min` | | `3000` | Freqüència mínima en kHz |
| `--freq-max` | | `55000` | Freqüència màxima en kHz |
| `--cluster-host` | | `dxc.pi4cc.nl` | Host del DX Cluster |
| `--cluster-port` | | `8000` | Port del DX Cluster |
| `--silence-start` | | `23` | Hora d'inici del silenci nocturn (0-23) |
| `--silence-end` | | `7` | Hora de fi del silenci nocturn (0-23) |
| | | | |
| **Club Log** | | | |
| `--clublog-api-key` | | `None` | API Key de Club Log |
| `--clublog-email` | | `None` | Email de Club Log |
| `--clublog-password` | | `None` | Password de Club Log |
| | | | |
| **Telegram** | | | |
| `--telegram-token` | | `None` | Token del bot Telegram |
| `--telegram-chat-id` | | `None` | Chat ID de Telegram |

### Comportament per mode

- **CW**: sempre ignorat (usa el mínim ample de banda, spots majoritàriament redundants)
- **FT8**: per defecte només alerta de països **mai treballats** (qualsevol any/mode). Inclou `FT8` a `--modes` per tractar-lo com qualsevol altre mode.
- **SSB, FT4, RTTY, MFSK**: controlats per `--modes`. Alerta si el combo (any, mode, entitat) no és al teu chart.
- **Altres modes**: si no es detecta cap mode conegut, es mostra en blanc (sense mode).

### Sistema d'alertes (Four-Tier)

El sistema compara cada spot amb tres fonts (Club Log lifetime chart + Club Log any actual treballat + Club Log any actual confirmat):

| Nivell | Condició | `--no-confirmed-only=OFF` | `--no-confirmed-only=ON` |
|--------|----------|:---:|:---:|
| 🚨 **Mai treballada** | No és al teu Club Log Chart (lifetime) | **24/7** | **24/7** |
| 🌅 **NO a l'any** | Treballada abans però no aquest any | **⏰ horari** | **⏰ horari** |
| 💤 **No confirmada** | Treballada l'any en curs, sense QSL | ❌ silenci | **⏰ horari** |
| ✅ Ja confirmada | Confirmada l'any en curs | ❌ silenci | ❌ silenci |

Les re-alertes (mateixa entitat, diferent freqüència) mostren "Nou avís, fa X min" o "QSY! era Y kHz" segons correspongui.

### Configuració Telegram

1. Crea un bot via [@BotFather](https://t.me/botfather) a Telegram
2. Obté el teu chat ID (escriu a [@userinfobot](https://t.me/userinfobot))
3. Passa'ls com a `--telegram-token` i `--telegram-chat-id`

### Exemple d'execució

```bash
python3 dxcc_clublog_v4.py \
    --callsign EB3AM \
    --cluster-login EB3AM \
    --clublog-api-key "TEU_API_KEY" \
    --clublog-email "teu@email.com" \
    --clublog-password "TEU_PASSWORD" \
    --telegram-token "123456:ABC" \
    --telegram-chat-id "987654" \
    --silence-start 3 \
    --silence-end 8
```

### Executar com a servei

**macOS (launchd)** — Crea `~/Library/LaunchAgents/com.teucall.dxspot.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.teucall.dxspot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/ruta/a/dxcc_clublog_v4.py</string>
        <string>--callsign</string>
        <string>TEUCALL</string>
        <string>--clublog-api-key</string>
        <string>KEY</string>
        <string>--clublog-email</string>
        <string>EMAIL</string>
        <string>--clublog-password</string>
        <string>PASS</string>
        <string>--telegram-token</string>
        <string>TOKEN</string>
        <string>--telegram-chat-id</string>
        <string>ID</string>
        <string>--silence-start</string>
        <string>3</string>
        <string>--silence-end</string>
        <string>8</string>
    </array>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
```
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.teucall.dxspot.plist
```

**Linux (systemd)** — Crea `/etc/systemd/system/dxspot.service`:
```ini
[Unit]
Description=DXSpot DXCC Monitor
After=network.target

[Service]
ExecStart=/usr/bin/python3 /ruta/a/dxcc_clublog_v4.py --callsign TEUCALL --clublog-api-key KEY --clublog-email EMAIL --clublog-password PASS --telegram-token TOKEN --telegram-chat-id ID --silence-start 3 --silence-end 8
Restart=always
RestartSec=10
User=TEU_USUARI

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload && systemctl enable --now dxspot
```

---

### 🔧 Fitxers generats

| Fitxer | Contingut |
|--------|-----------|
| `dxcc_prefixes.json` | Mapa de prefixos → entitats (generat per `parse_cty.py`) |
| `entity_codes.json` | Llista de codis DXCC numèrics |
| `clublog_dxcc_chart.json` | DXCC Chart descarregat de Club Log (cada 24h) |

⚠️ **No pugeu aquests fitxers a GitHub** — el `.gitignore` els exclou automàticament.

---

### 📁 Estructura del repositori

```
DXSpot/
├── dxcc_clublog_v4.py      # Monitor principal (recomanat)
├── dxcc_clublog_v3.bat     # Windows launcher
├── dxcc_clublog_v2.py      # Versió anterior (amb eQSL/ADIF)
├── dxcc_clublog_v2.bat     # Windows launcher v2
├── dxcc_clublog.py         # Versió encara anterior
├── dxcc_monitor.py         # Versió original (només cluster)
├── parse_cty.py            # Genera el mapa de prefixos
├── requirements.txt        # Dependències Python
├── README.md               # Aquest fitxer
└── .gitignore              # Exclou dades sensibles
```

---

## 📖 EN — English

Real-time DXCC entity monitor via Telnet DX Cluster + Club Log integration. Connects to a DX cluster, processes spots in real time, compares them against your Club Log charts (lifetime + current year), and sends Telegram alerts for new DXCC entities.

### Features

- **Real-time monitoring** — persistent Telnet connection to your preferred DX Cluster
- **Club Log lifetime chart** — downloads your DXCC Chart once per day to track never-worked entities
- **Club Log current year chart** — downloads `date=3` chart to track this year's worked entities
- **No ADIF/eQSL required** — no ADIF downloads, no eQSL credentials needed
- **Mode detection** — auto-detects FT8, FT4, CW, SSB, RTTY from spot comments, with frequency-based fallback
- **Telegram alerts** — two-tier notification system:
  - 🚨 **Never worked** (24/7)
  - 🌅 **Not worked this year** (daytime only, configurable silence hours)
- **Deduplication** — configurable re-alert interval (2h default)
- **QSY detection** — same prefix on a different frequency re-alerts with "QSY! was X kHz"
- **Auto-refresh** — prefix maps and Club Log charts refresh every 24h
- **Never-worked tracking** — maintains an up-to-date set of DXCC entities never contacted

### Requirements

- Python 3.8+
- `requests` — HTTP library
- `parse_cty.py` — generates `dxcc_prefixes.json` from ARRL's `cty.dat`
- Internet connection (DX Cluster, Club Log API)

### Installation

```bash
# Clone the repository
git clone https://github.com/TecnoTalarn/DXSpot.git
cd DXSpot

# Install dependencies
pip install requests

# Generate prefix map
python3 parse_cty.py        # generates dxcc_prefixes.json

# Initial setup
python3 dxcc_clublog_v4.py \
    --callsign YOURCALL \
    --clublog-api-key YOUR_CLUBLOG_API_KEY \
    --clublog-email YOUR_EMAIL \
    --clublog-password YOUR_PASSWORD \
    --telegram-token 123456:ABC \
    --telegram-chat-id 987654
```

### Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--callsign` | | **required** | Your callsign |
| `--cluster-login` | | = callsign | Callsign for cluster login (if different) |
| `--year` | `-y` | current year | Year for chart filtering and alerts |
| `--modes` | `-m` | `ALL` | Comma-separated modes (FT8,SSB,FT4...) or ALL |
| `--freq-min` | | `3000` | Min frequency in kHz |
| `--freq-max` | | `55000` | Max frequency in kHz |
| `--cluster-host` | | `dxc.pi4cc.nl` | DX Cluster hostname |
| `--cluster-port` | | `8000` | DX Cluster port |
| `--silence-start` | | `23` | Silence start hour (0-23) |
| `--silence-end` | | `7` | Silence end hour (0-23) |
| | | | |
| **Club Log** | | | |
| `--clublog-api-key` | | `None` | Club Log API Key |
| `--clublog-email` | | `None` | Club Log email |
| `--clublog-password` | | `None` | Club Log password |
| | | | |
| **Telegram** | | | |
| `--telegram-token` | | `None` | Telegram Bot API token |
| `--telegram-chat-id` | | `None` | Telegram chat ID |

### Example

```bash
python3 dxcc_clublog_v4.py \
    --callsign EB3AM \
    --cluster-login EB3AM \
    --clublog-api-key "YOUR_API_KEY" \
    --clublog-email "your@email.com" \
    --clublog-password "YOUR_PASSWORD" \
    --telegram-token "123456:ABC" \
    --telegram-chat-id "987654" \
    --silence-start 3 \
    --silence-end 8
```

### Running as a Service

**macOS (launchd)** — Create `~/Library/LaunchAgents/com.yourcall.dxspot.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yourcall.dxspot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/dxcc_clublog_v4.py</string>
        <string>--callsign</string>
        <string>YOURCALL</string>
        <string>--clublog-api-key</string>
        <string>KEY</string>
        <string>--clublog-email</string>
        <string>EMAIL</string>
        <string>--clublog-password</string>
        <string>PASS</string>
        <string>--telegram-token</string>
        <string>TOKEN</string>
        <string>--telegram-chat-id</string>
        <string>ID</string>
        <string>--silence-start</string>
        <string>3</string>
        <string>--silence-end</string>
        <string>8</string>
    </array>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
```
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yourcall.dxspot.plist
```

---

### 📁 Repository structure

```
DXSpot/
├── dxcc_clublog_v4.py      # Main monitor (recommended)
├── dxcc_clublog_v3.bat     # Windows launcher v3
├── dxcc_clublog_v2.py      # Previous version (with eQSL/ADIF)
├── dxcc_clublog_v2.bat     # Windows launcher v2
├── dxcc_clublog.py         # Older version
├── dxcc_monitor.py         # Original version (cluster only)
├── parse_cty.py            # Prefix map generator
├── requirements.txt        # Python dependencies
├── README.md               # This file
└── .gitignore              # Excludes sensitive data
```

---

## 📄 License | Llicència

MIT
