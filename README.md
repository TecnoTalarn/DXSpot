# DXSpot

Monitor d'entitats DXCC en temps real via DX Cluster Telnet | *Real-time DXCC entity monitor via Telnet DX Cluster*

---

## 📖 CAT — Català

Monitoritza spots en temps real des d'un DX Cluster, compara'ls amb el teu log ADIF i t'avisa per Telegram quan apareixen noves entitats (països).

### Funcionalitats

- **Monitor en temps real** — connexió Telnet persistent al teu DX Cluster preferit
- **Integració amb log ADIF** — llegeix el teu log (via eQSL o fitxer local) per evitar re-alertes d'entitats ja treballades
- **Detecció de mode** — detecta automàticament FT8, FT4, CW, SSB, RTTY, amb fallback per freqüència
- **Alertes Telegram** — notificacions configurables per a noves entitats DXCC
- **Silenci nocturn** — suprimeix alertes no crítiques entre 23:30 i 07:30
- **Deduplicació** — interval de re-alerta configurable (2h per defecte) per QSYs i re-spots
- **Entitats mai treballades** — manté una llista d'entitats DXCC mai contactades (qualsevol any/mode)

### Requisits

- Python 3.8+
- `requests` — llibreria HTTP
- `adif_io` — parser de fitxers ADIF
- `parse_cty.py` — genera `dxcc_prefixes.json` des del `cty.dat` de l'ARRL

### Instal·lació

```bash
cd DXSpot
pip install requests adif_io
python3 parse_cty.py        # genera dxcc_prefixes.json
python3 dxspot.py --callsign TEUCALL --telegram-token TOKEN --telegram-chat-id ID
```

### Arguments

| Argument | Curt | Per defecte | Descripció |
|----------|------|-------------|------------|
| `--callsign` | | **obligatori** | El teu indicatiu (per connectar al cluster) |
| `--year` | `-y` | any actual | Any per filtrar log i alertes |
| `--modes` | `-m` | `SSB` | Modes separats per coma |
| `--freq-min` | | `3000` | Freqüència mínima en kHz |
| `--freq-max` | | `55000` | Freqüència màxima en kHz |
| `--telegram-token` | | `None` | Token de l'API del bot Telegram |
| `--telegram-chat-id` | | `None` | Chat ID de Telegram |
| `--cluster-host` | | `dxc.pi4cc.nl` | Host del DX Cluster |
| `--cluster-port` | | `8000` | Port del DX Cluster |
| `--eqsl-user` | | `None` | Usuari eQSL (per baixar l'ADIF) |
| `--eqsl-pass` | | `None` | Contrasenya eQSL |

### Comportament per mode

- **CW**: sempre ignorat (utilitza un cluster específic per CW si cal)
- **FT8**: per defecte només alerta de països mai treballats (qualsevol any/mode). Inclou `FT8` a `--modes` per tractar-lo com qualsevol altre mode.
- **SSB, FT4, RTTY, MFSK**: controlats per `--modes`. Només alerta si el combo (any, mode, entitat) no és al teu log.

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
        <string>/ruta/a/dxspot.py</string>
        <string>--callsign</string>
        <string>TEUCALL</string>
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
ExecStart=/usr/bin/python3 /ruta/a/dxspot.py --callsign TEUCALL --telegram-token TOKEN --telegram-chat-id ID
Restart=always
RestartSec=10
User=TEU_USUARI

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload && systemctl enable --now dxspot
```

**Windows (Task Scheduler)** — Crea una tasca programada que executi `python3 C:\ruta\a\dxspot.py --callsign TEUCALL ...` a l'inici de sessió.

---

## 📖 EN — English

Real-time DXCC entity spotter via Telnet DX Cluster. Connects to a DX cluster, processes spots in real time, compares them against your ADIF log, and sends Telegram alerts for new entities.

### Features

- **Real-time monitoring** — persistent Telnet connection to your preferred DX Cluster
- **ADIF log integration** — reads your log (via eQSL download or local ADIF file) to avoid re-alerting on already-worked entities
- **Mode detection** — auto-detects FT8, FT4, CW, SSB, RTTY from spot comments, with frequency-based fallback
- **Telegram alerts** — configurable notifications for new DXCC entities
- **Quiet hours** — suppresses non-critical alerts overnight (23:30–07:30)
- **Entity deduplication** — configurable re-alert interval (2h default) for QSYs and re-spots
- **Never-worked tracking** — maintains a list of DXCC entities never worked (any year, any mode)

### Requirements

- Python 3.8+
- `requests` — HTTP library
- `adif_io` — ADIF file parser
- `parse_cty.py` — generates `dxcc_prefixes.json` from ARRL `cty.dat`

### Installation

```bash
cd DXSpot
pip install requests adif_io
python3 parse_cty.py        # generates dxcc_prefixes.json
python3 dxspot.py --callsign YOURCALL --telegram-token TOKEN --telegram-chat-id ID
```

### Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--callsign` | | **required** | Your callsign (used to connect to DX cluster) |
| `--year` | `-y` | current year | Year to filter log and alerts |
| `--modes` | `-m` | `SSB` | Comma-separated modes to monitor |
| `--freq-min` | | `3000` | Min frequency in kHz |
| `--freq-max` | | `55000` | Max frequency in kHz |
| `--telegram-token` | | `None` | Telegram Bot API token |
| `--telegram-chat-id` | | `None` | Telegram chat ID |
| `--cluster-host` | | `dxc.pi4cc.nl` | DX Cluster hostname |
| `--cluster-port` | | `8000` | DX Cluster port |
| `--eqsl-user` | | `None` | eQSL username (for ADIF download) |
| `--eqsl-pass` | | `None` | eQSL password (for ADIF download) |

### Mode Behaviour

- **CW**: always ignored (use a CW-specific cluster if needed)
- **FT8**: by default, only alerts for never-worked countries (any year/mode). Include `FT8` in `--modes` to treat it like any other mode.
- **SSB, FT4, RTTY, MFSK**: controlled by `--modes`. Only alerts if the (year, mode, entity) combo is not in your log.

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
        <string>/path/to/dxspot.py</string>
        <string>--callsign</string>
        <string>YOURCALL</string>
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
ExecStart=/usr/bin/python3 /path/to/dxspot.py --callsign YOURCALL --telegram-token TOKEN --telegram-chat-id ID
Restart=always
RestartSec=10
User=YOUR_USER

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload && systemctl enable --now dxspot
```

**Windows (Task Scheduler)** — Create a scheduled task running `python3 C:\path\to\dxspot.py --callsign YOURCALL ...` at user logon.

---

## 📦 Dependencies | Dependències

- `dxcc_prefixes.json` — generated by `parse_cty.py` from ARRL's `cty.dat` | generat per `parse_cty.py` des del `cty.dat` de l'ARRL
- `logbook.adi` — downloaded from eQSL (optional) | baixat d'eQSL (opcional)

## 📄 License | Llicència

MIT
