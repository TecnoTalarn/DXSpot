# DXSpot

Monitor d'entitats DXCC en temps real via DX Cluster + Club Log | *Real-time DXCC entity monitor via DX Cluster + Club Log*

---

## 📖 CAT — Català

Monitoritza spots en temps real des d'un DX Cluster, compara'ls amb el teu log (Club Log + eQSL) i t'avisa per Telegram de noves entitats DXCC.

### Funcionalitats

- **Monitor en temps real** — connexió Telnet persistent al teu DX Cluster preferit
- **Integració Club Log** — baixa el teu DXCC Chart (lifetime) i l'usa per saber quines entitats has treballat mai
- **Integració eQSL** — baixa l'ADIF automàticament cada 24h per saber quines entitats has treballat l'any en curs
- **Integració ADIF local** — pots passar un fitxer ADIF directament (alternativa a eQSL)
- **Detecció de mode** — detecta automàticament FT8, FT4, CW, SSB, RTTY, amb fallback per freqüència
- **Alertes Telegram** — notificacions configurables amb dos nivells:
  - 🚨 **Mai treballada** (24/7)
  - 🌅 **NO treballada l'any en curs** (només 7:00-23:00 hora local)
- **Deduplicació** — control de re-alertes amb interval configurable (2h per defecte)
- **QSY detection** — si el mateix prefix apareix a una freqüència diferent, re-alerta amb "QSY! era X kHz"
- **Silenci nocturn** — les entitats ja treballades (però no aquest any) només alerten de dia
- **Actualització automàtica** — els mapes de prefixos i el chart de Club Log es refresquen cada 24h
- **Llista d'entitats mai treballades** — manté un set actualitzat per saber què falta

### Requisits

- Python 3.8+
- `requests` — llibreria HTTP
- `adif_io` — parser de fitxers ADIF
- `parse_cty.py` — genera `dxcc_prefixes.json` des del `cty.dat` de l'ARRL
- Connexió a internet (DX Cluster, Club Log API, eQSL)

### Instal·lació

```bash
# Clonar el repositori
git clone https://github.com/TEU_USUARI/dxspot.git
cd dxspot

# Instal·lar dependències
pip install requests adif_io

# Generar mapa de prefixos
python3 parse_cty.py        # genera dxcc_prefixes.json

# Configuració inicial (crea el json de chart)
python3 dxcc_clublog_v2.py \
    --callsign TEUCALL \
    --clublog-api-key TEU_CLUBLOG_API_KEY \
    --clublog-email TEU_EMAIL \
    --clublog-password TEU_PASSWORD \
    --adif /ruta/al/teu/log.adi \
    --telegram-token 123456:ABC \
    --telegram-chat-id 987654
```

### Arguments

| Argument | Curt | Per defecte | Descripció |
|----------|------|-------------|------------|
| `--callsign` | | **obligatori** | El teu indicatiu |
| `--cluster-login` | | = callsign | Indicatiu pel login al cluster (si és diferent) |
| `--year` | `-y` | any actual | Any per filtrar log i alertes |
| `--modes` | `-m` | `ALL` | Modes separats per coma (FT8,SSB,FT4...) o ALL |
| `--freq-min` | | `3000` | Freqüència mínima en kHz |
| `--freq-max` | | `55000` | Freqüència màxima en kHz |
| `--cluster-host` | | `dxc.pi4cc.nl` | Host del DX Cluster |
| `--cluster-port` | | `8000` | Port del DX Cluster |
| | | | |
| **Club Log** | | | |
| `--clublog-api-key` | | `None` | API Key de Club Log (per chart i lookup) |
| `--clublog-email` | | `None` | Email de Club Log |
| `--clublog-password` | | `None` | Password de Club Log |
| | | | |
| **ADIF / eQSL** | | | |
| `--adif` | | `None` | Ruta al fitxer ADIF local |
| `--eqsl-user` | | `None` | Usuari eQSL (per baixada automàtica ADIF) |
| `--eqsl-pass` | | `None` | Contrasenya eQSL |
| | | | |
| **Telegram** | | | |
| `--telegram-token` | | `None` | Token del bot Telegram |
| `--telegram-chat-id` | | `None` | Chat ID de Telegram |

### Comportament per mode

- **CW**: sempre ignorat (usa el mínim ample de banda, spots majoritàriament redundants)
- **FT8**: per defecte només alerta de països **mai treballats** (qualsevol any/mode). Inclou `FT8` a `--modes` per tractar-lo com qualsevol altre mode.
- **SSB, FT4, RTTY, MFSK**: controlats per `--modes`. Alerta si el combo (any, mode, entitat) no és al teu log.
- **Altres modes**: si no es detecta cap mode conegut, es mostra en blanc (sense mode).

### Sistema d'alertes (Two-Tier)

El sistema compara cada spot amb dues fonts:

| Nivell | Condició | Quan alerta |
|--------|----------|-------------|
| 🚨 **Mai treballada** | No és al teu Club Log Chart (lifetime) | **24/7** |
| 🌅 **NO a l'any** | Treballada abans però no aquest any | **7:00 - 23:00** |
| ✅ Ja treballada | Al teu ADIF de l'any en curs | Silenci |

Les re-alertes (mateixa entitat, diferent freqüència) mostren "Nou avís, fa X min" o "QSY! era Y kHz" segons correspongui.

### Configuració Telegram

1. Crea un bot via [@BotFather](https://t.me/botfather) a Telegram
2. Obté el teu chat ID (escriu a [@userinfobot](https://t.me/userinfobot))
3. Passa'ls com a `--telegram-token` i `--telegram-chat-id`

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
        <string>/ruta/a/dxcc_clublog_v2.py</string>
        <string>--callsign</string>
        <string>TEUCALL</string>
        <string>--clublog-api-key</string>
        <string>KEY</string>
        <string>--clublog-email</string>
        <string>EMAIL</string>
        <string>--clublog-password</string>
        <string>PASS</string>
        <string>--adif</string>
        <string>/ruta/a/logbook.adi</string>
        <string>--telegram-token</string>
        <string>TOKEN</string>
        <string>--telegram-chat-id</string>
        <string>ID</string>
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
ExecStart=/usr/bin/python3 /ruta/a/dxcc_clublog_v2.py --callsign TEUCALL --clublog-api-key KEY --clublog-email EMAIL --clublog-password PASS --adif /ruta/a/logbook.adi --telegram-token TOKEN --telegram-chat-id ID
Restart=always
RestartSec=10
User=TEU_USUARI

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload && systemctl enable --now dxspot
```

**Windows (Task Scheduler)** — Crea una tasca programada que executin `python3 C:\ruta\a\dxcc_clublog_v2.py --callsign TEUCALL ...` a l'inici de sessió.

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
├── dxcc_clublog_v2.py      # Monitor principal (recomanat)
├── dxcc_clublog_v2.bat     # Windows launcher (comprova Python + deps)
├── dxcc_clublog.py         # Versió anterior
├── dxcc_monitor.py         # Versió original (només cluster)
├── parse_cty.py            # Genera el mapa de prefixos
├── requirements.txt        # Dependències Python
├── README.md               # Aquest fitxer
└── .gitignore              # Exclou dades sensibles
```

---

## 📖 EN — English

Real-time DXCC entity monitor via Telnet DX Cluster + Club Log integration. Connects to a DX cluster, processes spots in real time, compares them against your logs (Club Log chart + ADIF), and sends Telegram alerts for new DXCC entities.

### Features

- **Real-time monitoring** — persistent Telnet connection to your preferred DX Cluster
- **Club Log integration** — downloads your DXCC Chart (lifetime) once per day to track worked entities
- **eQSL integration** — auto-downloads your ADIF log every 24h to track current year worked entities
- **Local ADIF support** — supply a local ADIF file as alternative to eQSL
- **Mode detection** — auto-detects FT8, FT4, CW, SSB, RTTY from spot comments, with frequency-based fallback
- **Telegram alerts** — two-tier notification system:
  - 🚨 **Never worked** (24/7)
  - 🌅 **Not worked this year** (07:00-23:00 local time)
- **Deduplication** — configurable re-alert interval (2h default)
- **QSY detection** — same prefix on a different frequency re-alerts with "QSY! was X kHz"
- **Auto-refresh** — prefix maps and Club Log chart refresh every 24h
- **Never-worked tracking** — maintains an up-to-date set of DXCC entities never contacted

### Requirements

- Python 3.8+
- `requests` — HTTP library
- `adif_io` — ADIF file parser
- `parse_cty.py` — generates `dxcc_prefixes.json` from ARRL's `cty.dat`
- Internet connection (DX Cluster, Club Log API, eQSL)

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USER/dxspot.git
cd dxspot

# Install dependencies
pip install requests adif_io

# Generate prefix map
python3 parse_cty.py        # generates dxcc_prefixes.json

# Initial setup (creates chart cache)
python3 dxcc_clublog_v2.py \
    --callsign YOURCALL \
    --clublog-api-key YOUR_CLUBLOG_API_KEY \
    --clublog-email YOUR_EMAIL \
    --clublog-password YOUR_PASSWORD \
    --adif /path/to/your/log.adi \
    --telegram-token 123456:ABC \
    --telegram-chat-id 987654
```

### Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--callsign` | | **required** | Your callsign |
| `--cluster-login` | | = callsign | Callsign for cluster login (if different) |
| `--year` | `-y` | current year | Year to filter log and alerts |
| `--modes` | `-m` | `ALL` | Comma-separated modes (FT8,SSB,FT4...) or ALL |
| `--freq-min` | | `3000` | Min frequency in kHz |
| `--freq-max` | | `55000` | Max frequency in kHz |
| `--cluster-host` | | `dxc.pi4cc.nl` | DX Cluster hostname |
| `--cluster-port` | | `8000` | DX Cluster port |
| | | | |
| **Club Log** | | | |
| `--clublog-api-key` | | `None` | Club Log API Key (for chart + lookup) |
| `--clublog-email` | | `None` | Club Log email |
| `--clublog-password` | | `None` | Club Log password |
| | | | |
| **ADIF / eQSL** | | | |
| `--adif` | | `None` | Path to local ADIF file |
| `--eqsl-user` | | `None` | eQSL username (for automatic ADIF download) |
| `--eqsl-pass` | | `None` | eQSL password |
| | | | |
| **Telegram** | | | |
| `--telegram-token` | | `None` | Telegram Bot API token |
| `--telegram-chat-id` | | `None` | Telegram chat ID |

### Mode Behaviour

- **CW**: always ignored (uses minimal bandwidth, spots are mostly redundant)
- **FT8**: by default, only alerts for **never-worked** countries (any year/mode). Include `FT8` in `--modes` to treat it like any other mode.
- **SSB, FT4, RTTY, MFSK**: controlled by `--modes`. Alerts if the (year, mode, entity) combo is not in your log.
- **Unknown modes**: displayed blank (no mode shown).

### Alert System (Two-Tier)

Each spot is compared against two sources:

| Tier | Condition | When it alerts |
|------|-----------|----------------|
| 🚨 **Never worked** | Not in your Club Log Chart (lifetime) | **24/7** |
| 🌅 **Not this year** | Worked before, but not this year | **07:00 - 23:00** |
| ✅ Already worked | In your current year ADIF | Silent |

Re-alerts (same entity, different frequency) show "Nou avís, fa X min" or "QSY! was Y kHz" as appropriate (Catalan alerts).

### Telegram Setup

1. Create a bot via [@BotFather](https://t.me/botfather) on Telegram
2. Get your chat ID (message [@userinfobot](https://t.me/userinfobot))
3. Pass both as `--telegram-token` and `--telegram-chat-id`

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
        <string>/path/to/dxcc_clublog_v2.py</string>
        <string>--callsign</string>
        <string>YOURCALL</string>
        <string>--clublog-api-key</string>
        <string>KEY</string>
        <string>--clublog-email</string>
        <string>EMAIL</string>
        <string>--clublog-password</string>
        <string>PASS</string>
        <string>--adif</string>
        <string>/path/to/logbook.adi</string>
        <string>--telegram-token</string>
        <string>TOKEN</string>
        <string>--telegram-chat-id</string>
        <string>ID</string>
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

**Linux (systemd)** — Create `/etc/systemd/system/dxspot.service`:
```ini
[Unit]
Description=DXSpot DXCC Monitor
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/dxcc_clublog_v2.py --callsign YOURCALL --clublog-api-key KEY --clublog-email EMAIL --clublog-password PASS --adif /path/to/logbook.adi --telegram-token TOKEN --telegram-chat-id ID
Restart=always
RestartSec=10
User=YOUR_USER

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload && systemctl enable --now dxspot
```

**Windows (Task Scheduler)** — Create a scheduled task running `python3 C:\path\to\dxcc_clublog_v2.py --callsign YOURCALL ...` at user logon.

---

### 🔧 Generated files

| File | Content |
|------|---------|
| `dxcc_prefixes.json` | Prefix → entity map (generated by `parse_cty.py`) |
| `entity_codes.json` | DXCC numeric code list |
| `clublog_dxcc_chart.json` | Club Log DXCC Chart (downloaded every 24h) |

⚠️ **Do not upload these files to GitHub** — the `.gitignore` excludes them automatically.

---

### 📁 Repository structure

```
DXSpot/
├── dxcc_clublog_v2.py      # Main monitor (recommended)
├── dxcc_clublog_v2.bat     # Windows launcher (checks Python + deps)
├── dxcc_clublog.py         # Previous version
├── dxcc_monitor.py         # Original version (cluster only)
├── parse_cty.py            # Prefix map generator
├── requirements.txt        # Python dependencies
├── README.md               # This file
└── .gitignore              # Excludes sensitive data
```

---

## 📄 License | Llicència

MIT
