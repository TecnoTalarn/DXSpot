# DXCC Monitor

Real-time DXCC entity monitor via Telnet DX Cluster. Connects to a DX cluster, processes spots in real time, compares them against your ADIF log, and sends Telegram alerts when new entities (countries) are spotted.

## Features

- **Real-time monitoring** — persistent Telnet connection to your preferred DX Cluster
- **ADIF log integration** — reads your log (via eQSL download or local ADIF file) to avoid re-alerting on already-worked entities
- **Mode detection** — auto-detects FT8, FT4, CW, SSB, RTTY from spot comments, with frequency-based fallback
- **Telegram alerts** — configurable notifications for new DXCC entities
- **Quiet hours** — suppresses non-critical alerts overnight (23:30–07:30)
- **Entity deduplication** — configurable re-alert interval (2h default) for QSYs and re-spots
- **Never-worked tracking** — maintains a list of DXCC entities never worked (any year, any mode)

## Requirements

- Python 3.8+
- `requests` — HTTP library
- `adif_io` — ADIF file parser
- `parse_cty.py` — generates `dxcc_prefixes.json` from ARRL `cty.dat`

## Installation

```bash
# Clone or download the files
cd dxcc_monitor

# Install dependencies
pip install requests adif_io

# Generate the DXCC prefix map
python3 parse_cty.py  # outputs dxcc_prefixes.json

# Test the monitor
python3 dxcc_monitor.py --callsign YOURCALL \
  --telegram-token 123456:ABC \
  --telegram-chat-id 987654
```

## Usage

### Basic
```bash
python3 dxcc_monitor.py --callsign YOURCALL \
  --telegram-token YOUR_BOT_TOKEN \
  --telegram-chat-id YOUR_CHAT_ID
```

### With filters
```bash
python3 dxcc_monitor.py --callsign YOURCALL \
  --telegram-token TOKEN --telegram-chat-id ID \
  --year 2026 \
  --modes SSB,FT8 \
  --freq-min 3000 --freq-max 55000
```

### Without Telegram (console only)
```bash
python3 dxcc_monitor.py --callsign YOURCALL
```

### With eQSL log download
```bash
python3 dxcc_monitor.py --callsign YOURCALL \
  --telegram-token TOKEN --telegram-chat-id ID \
  --eqsl-user YOURCALL --eqsl-pass YOURPASS
```

## Arguments

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

## Mode Behaviour

- **CW**: always ignored (use a CW-specific cluster if needed)
- **FT8**: by default, only alerts for countries never worked (any year/mode). Include FT8 in `--modes` to treat it like any other mode.
- **SSB, FT4, RTTY, MFSK**: controlled by `--modes`. Only alerts if the mode is in the list AND the (year, mode, entity) combo is not in your log.

## Telegram Setup

1. Create a bot via [@BotFather](https://t.me/botfather) on Telegram
2. Get your chat ID (message [@userinfobot](https://t.me/userinfobot))
3. Pass both as `--telegram-token` and `--telegram-chat-id`

## Running as a Service

### macOS (launchd)
Create `~/Library/LaunchAgents/com.yourcall.dxcc-monitor.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yourcall.dxcc-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/dxcc_monitor.py</string>
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
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.yourcall.dxcc-monitor.plist
```

### Linux (systemd)
Create `/etc/systemd/system/dxcc-monitor.service`:

```ini
[Unit]
Description=DXCC Monitor
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/dxcc_monitor.py \
  --callsign YOURCALL \
  --telegram-token TOKEN \
  --telegram-chat-id ID
Restart=always
RestartSec=10
User=YOUR_USER

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable dxcc-monitor
systemctl start dxcc-monitor
```

### Windows (Task Scheduler)
Create a scheduled task that runs `python3 C:\path\to\dxcc_monitor.py --callsign YOURCALL ...` at user logon, with "Run whether user is logged on or not" and "Restart if the task fails".

## Dependencies

- `dxcc_prefixes.json` — generated by the companion `parse_cty.py` script from ARRL's `cty.dat`
- `logbook.adi` — downloaded from eQSL (optional, provide `--eqsl-user`/`--eqsl-pass`)

## License

MIT
