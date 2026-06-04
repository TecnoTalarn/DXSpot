#!/usr/bin/env python3
"""
dxcc_clublog_v2.py — DXCC Monitor via Club Log (sense eQSL/ADIF)
Basat en dxcc_monitor.py (connexió cluster provada i funcional)
Afegit: Club Log chart, two-tier alerting, entity codes.

Usage:
    python3 dxcc_clublog_v2.py --callsign EB3AM --cluster-login EB3AM-9 \\
        --clublog-api-key KEY --clublog-email EMAIL --clublog-password PASS \\
        --adif /path/to/logbook.adi --telegram-token TOKEN --telegram-chat-id ID
"""

import socket
import re
import json
import time
import os
import argparse
import requests
import threading
import subprocess
import adif_io
from datetime import datetime

# ===================== CONFIGURATION =====================
WORKSPACE = os.path.dirname(os.path.abspath(__file__))

# ===================== ARGPARSE =====================
def parse_args():
    parser = argparse.ArgumentParser(
        description="Real-time DXCC monitor via Club Log + DX Cluster",
        epilog="""Example: python3 dxcc_clublog_v2.py --callsign EB3AM \\
  --clublog-api-key KEY --clublog-email EMAIL --clublog-password PASS \\
  --telegram-token 123456:ABC --telegram-chat-id 987654"""
    )
    current_yr = str(datetime.now().year)
    # Filters
    parser.add_argument("--year", "-y", default=current_yr,
                        help=f"Year to filter (default: {current_yr})")
    parser.add_argument("--modes", "-m", default="ALL",
                        help="Comma-separated modes or ALL (default: ALL)")
    parser.add_argument("--freq-min", type=float, default=3000,
                        help="Min frequency in kHz (default: 3000 ~80m)")
    parser.add_argument("--freq-max", type=float, default=55000,
                        help="Max frequency in kHz (default: 55000 ~6m)")
    # Club Log
    parser.add_argument("--eqsl-user", default=None,
                        help="eQSL username (for ADIF download)")
    parser.add_argument("--eqsl-pass", default=None,
                        help="eQSL password (for ADIF download)")
    parser.add_argument("--clublog-api-key", default=None,
                        help="Club Log API key")
    parser.add_argument("--clublog-email", default=None,
                        help="Club Log email (for dxcc chart)")
    parser.add_argument("--clublog-password", default=None,
                        help="Club Log password (for dxcc chart)")
    parser.add_argument("--adif", default=None,
                        help="Path to logbook.adi (for 2026 worked entities)")
    # Connections
    parser.add_argument("--telegram-token", default=None,
                        help="Telegram Bot API token")
    parser.add_argument("--telegram-chat-id", default=None,
                        help="Telegram chat ID to send alerts to")
    parser.add_argument("--cluster-host", default="dxc.pi4cc.nl",
                        help="DX Cluster host (default: dxc.pi4cc.nl)")
    parser.add_argument("--cluster-port", type=int, default=8000,
                        help="DX Cluster port (default: 8000)")
    parser.add_argument("--callsign", required=True,
                        help="Your callsign (for Club Log chart)")
    parser.add_argument("--cluster-login", default=None,
                        help="Callsign for cluster login (default: same as --callsign)")
    args = parser.parse_args()

    if args.telegram_token and not args.telegram_chat_id:
        parser.error("--telegram-chat-id is required when --telegram-token is set")

    return args

# Globals
ARGS = None

# Prefix map files
PREFIX_FILE = os.path.join(WORKSPACE, "dxcc_prefixes.json")
ENTITY_CODES_FILE = os.path.join(WORKSPACE, "entity_codes.json")
CHART_CACHE = os.path.join(WORKSPACE, "clublog_dxcc_chart.json")
ADIF_FILE = None  # es resol en main()

# ===================== QUIET HOURS =====================

def is_daytime():
    """Returns True during 07:00-23:00 local time (alerting hours)."""
    now = datetime.now()
    current = now.hour * 60 + now.minute
    end = 23 * 60      # 23:00
    start = 7 * 60      # 07:00
    if start <= current < end:
        return True
    return False

# ===================== INIT =====================

# Spot regex: "DX de SPOTTER: FREQ DX_CALL COMMENT"
SPOT_RE = re.compile(r"^DX\s+de\s+(\S+):\s+([0-9.]+)\s+([A-Z0-9/]+)(.*)", re.IGNORECASE)

# Worked sets
worked_chart_codes = set()    # set of DXCC entity codes (lifetime, from Club Log)
worked_2026_codes = set()     # set of DXCC entity codes (2026, from ADIF)
FILTER_YEAR = "2026"          # Any de referència per al filtre
UNMATCHED_WORKED_NAMES = set()  # entity names in ADIF that weren't in entity_codes.json

last_alert_time = {}   # (entity_code,) -> timestamp
last_freq = {}         # (entity_code,) -> freq_khz
REALERT_HOURS = 2

# Prefix map
dxcc_prefixes = {}
sorted_prefixes = []
dxcc_exact = {}
dxcc_excludes = {}
dxcc_entities = []
region_map = {}

# Entity codes: entity_name -> DXCC code
entity_codes = {}
entity_codes_reverse = {}   # code -> name cache


def load_prefix_map():
    global dxcc_prefixes, sorted_prefixes, dxcc_exact, dxcc_excludes
    if os.path.exists(PREFIX_FILE):
        with open(PREFIX_FILE) as f:
            data = json.load(f)
        dxcc_prefixes = data["map"]
        sorted_prefixes = data["prefixes"]
        dxcc_exact = data.get("exact", {})
        dxcc_excludes = data.get("excludes", {})
        dxcc_entities[:] = data.get("dxcc_entities", [])
        region_map.clear()
        region_map.update(data.get("region_map", {}))
        return True
    print("dxcc_prefixes.json not found.")
    return False


def lookup_entity(callsign):
    """Longest-prefix match with cty.dat exceptions."""
    raw = callsign.upper()
    cs = raw.replace("/", " ")
    base_call = cs.split()[0]

    kg4_match = re.match(r'^KG4([A-Z]{1,3})$', base_call)
    if kg4_match:
        suffix_len = len(kg4_match.group(1))
        if suffix_len != 2 and suffix_len != 0:
            return "United States"

    if raw in dxcc_exact:
        return dxcc_exact[raw]
    if base_call in dxcc_exact:
        return dxcc_exact[base_call]

    if '/' in raw:
        suffix = raw.split('/')[-1]
        if suffix in dxcc_prefixes:
            return dxcc_prefixes[suffix]
        best_len = 0
        best = None
        for p in sorted_prefixes:
            if suffix.startswith(p) and len(p) > best_len:
                best_len = len(p)
                best = dxcc_prefixes[p]
        if best:
            return best
        base_prefix = ""
        for p in sorted_prefixes:
            if base_call.startswith(p):
                base_prefix = p
                break
        if base_prefix:
            portable_candidate = f"{base_prefix}/{suffix}"
            if portable_candidate in dxcc_prefixes:
                return dxcc_prefixes[portable_candidate]
            for p in sorted_prefixes:
                if portable_candidate.startswith(p) and len(p) > len(base_prefix):
                    return dxcc_prefixes[p]

    best_len = 0
    best = "UNKNOWN"
    for p in sorted_prefixes:
        if cs.startswith(p) and len(p) > best_len:
            if dxcc_excludes.get(base_call) == p:
                continue
            best_len = len(p)
            best = dxcc_prefixes[p]
    return best


# ===================== ENTITY CODES =====================

def load_entity_codes():
    """Load entity_codes.json into global entity_codes dict."""
    global entity_codes, entity_codes_reverse
    if not os.path.exists(ENTITY_CODES_FILE):
        print(f"entity_codes.json not found: {ENTITY_CODES_FILE}")
        return False
    with open(ENTITY_CODES_FILE) as f:
        entity_codes = json.load(f)
    entity_codes_reverse.clear()
    for name, code in entity_codes.items():
        entity_codes_reverse.setdefault(str(code), set()).add(name)
    print(f"Entity codes: {len(entity_codes)}")
    return True


def entity_to_code(entity_name):
    """Convert entity name (from prefix map) to DXCC code.
    Returns string code or None (str for consistent set comparisons).
    """
    code = entity_codes.get(entity_name.upper())
    if code is not None:
        return str(code)
    return None


# ===================== CLUB LOG CHART =====================

def clublog_download_chart():
    """Download DXCC chart from Club Log and cache locally."""
    global worked_chart_codes
    if not ARGS.clublog_email or not ARGS.clublog_password or not ARGS.clublog_api_key:
        print("Club Log credentials not configured")
        return False
    url = "https://clublog.org/json_dxccchart.php"
    params = {
        "call": ARGS.callsign,
        "api": ARGS.clublog_api_key,
        "email": ARGS.clublog_email,
        "password": ARGS.clublog_password,
        "mode": 0,
        "date": 0,
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        # data is dict: {dxcc_code: {band: status, ...}, ...}
        # status: 1=worked, 2=confirmed, 3=verified, True=worked
        codes = set()
        for code_str, bands in data.items():
            if isinstance(bands, dict):
                for band, status in bands.items():
                    if status in (1, 2, 3, True):
                        try:
                            codes.add(str(int(code_str)))
                        except ValueError:
                            pass
                        break
        worked_chart_codes = codes
        # Cache to file
        with open(CHART_CACHE, "w") as f:
            json.dump(data, f)
        print(f"📡 Club Log chart: {len(worked_chart_codes)} entitats")
        return True
    except Exception as e:
        print(f"Club Log chart error: {e}")
        # Try loading cache
        if os.path.exists(CHART_CACHE):
            with open(CHART_CACHE) as f:
                data = json.load(f)
            codes = set()
            for code_str, bands in data.items():
                if isinstance(bands, dict):
                    for band, status in bands.items():
                        if status in (1, 2, 3, True):
                            try:
                                codes.add(str(int(code_str)))
                            except ValueError:
                                pass
                            break
            worked_chart_codes = codes
            print(f"📡 Club Log chart (cached): {len(worked_chart_codes)} entitats")
            return True
        return False


# ===================== eQSL ADIF DOWNLOAD =====================

def download_adif_from_eqsl():
    """Descarrega el LOG COMPLET d'eQSL (OutBox - QSOs pujats per l'usuari)."""
    import html.parser

    class LinkExtractor(html.parser.HTMLParser):
        def __init__(self):
            super().__init__()
            self.adif_url = None
        def handle_starttag(self, tag, attrs):
            if tag == "a":
                attrs_dict = dict(attrs)
                href = attrs_dict.get("href", "")
                if href.endswith(".adi"):
                    self.adif_url = href

    if not ARGS.eqsl_user or not ARGS.eqsl_pass:
        print("eQSL credentials not configured")
        return False

    # Pas 1: obtenir pàgina amb enllaços
    url_api = f"https://www.eqsl.cc/qslcard/DownloadADIF.cfm?UserName={ARGS.eqsl_user}&Password={ARGS.eqsl_pass}&HamOnly=1"
    try:
        r = requests.get(url_api, timeout=60)
        r.raise_for_status()
        parser = LinkExtractor()
        parser.feed(r.text)
        if not parser.adif_url:
            print("No s'ha trobat enllaç ADIF a la resposta d'eQSL")
            return False
        if parser.adif_url.startswith("../"):
            parser.adif_url = "https://www.eqsl.cc/" + parser.adif_url[3:]
        print(f"Enllaç ADIF: {parser.adif_url}")
    except Exception as e:
        print(f"Error obtenint enllaç ADIF: {e}")
        return False

    # Pas 2: descarregar el fitxer ADIF
    try:
        r2 = requests.get(parser.adif_url, timeout=60)
        r2.raise_for_status()
        clean = r2.content.decode("utf-8", errors="replace").encode("utf-8", errors="replace")
        with open(os.path.abspath(ARGS.adif), "wb") as f:
            f.write(clean)
        print(f"ADIF descarregat ({len(clean)} bytes)")
        return True
    except Exception as e:
        print(f"Error descarregant ADIF: {e}")
        return False


def clublog_lookup_api(call):
    """Fallback: look up a single callsign via Club Log /dxcc API."""
    if not ARGS.clublog_api_key:
        return None
    try:
        r = requests.get("https://clublog.org/dxcc", params={
            "call": call, "full": 1, "api": ARGS.clublog_api_key
        }, timeout=10)
        r.raise_for_status()
        data = r.json()
        return str(data.get("dxcc", ""))
    except:
        return None


# ===================== ADIF 2026 =====================

def load_adif_2026(adif_path):
    """Load ADIF file and extract DXCC entities worked in 2026."""
    global worked_2026_codes, UNMATCHED_WORKED_NAMES
    if not adif_path or not os.path.exists(adif_path):
        print(f"ADIF not found: {adif_path}")
        return False
    try:
        with open(adif_path, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8", errors="replace")
        qsos, _ = adif_io.read_from_string(text)
    except Exception as e:
        print(f"Error parsing ADIF: {e}")
        return False

    worked_2026_codes.clear()
    UNMATCHED_WORKED_NAMES.clear()
    count = 0
    for qso in qsos:
        date = qso.get("QSO_DATE", "")
        year = date[:4] if len(date) >= 4 else ""
        if year != FILTER_YEAR:
            continue
        call = qso.get("CALL", "").upper()
        if not call:
            continue
        entity = lookup_entity(call)
        if entity and entity != "UNKNOWN":
            code = entity_to_code(entity)
            if code:
                worked_2026_codes.add(code)
            else:
                UNMATCHED_WORKED_NAMES.add(entity)
        count += 1

    print(f"📄 ADIF {FILTER_YEAR}: {count} QSOs, {len(worked_2026_codes)} entitats")
    if UNMATCHED_WORKED_NAMES:
        print(f"⚠️  {len(UNMATCHED_WORKED_NAMES)} entitats sense codi DXCC")
    return True


# ===================== MODE GUESSING =====================

def guess_mode(freq_khz, comment):
    """Guess mode from comment text, fallback to frequency band."""
    c = comment.upper()
    if "FT8" in c: return "FT8"
    if "FT4" in c: return "FT4"
    if "CW" in c: return "CW"
    if "SSB" in c: return "SSB"
    if "RTTY" in c: return "RTTY"
    if 14000 <= freq_khz <= 14070: return "CW"
    if 21000 <= freq_khz <= 21070: return "CW"
    if 7000 <= freq_khz <= 7040: return "CW"
    if (7074 <= freq_khz <= 7076) or (14074 <= freq_khz <= 14076): return "FT8"
    if 14100 <= freq_khz <= 14350: return "SSB"
    return "UNKNOWN"


# ===================== TELEGRAM =====================

def send_telegram(msg):
    """Send a message via Telegram Bot API."""
    if not ARGS.telegram_token or not ARGS.telegram_chat_id:
        print(f"[Telegram would send] {msg}")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{ARGS.telegram_token}/sendMessage",
            json={"chat_id": ARGS.telegram_chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=5
        )
    except Exception as e:
        print(f"Telegram error: {e}")


# ===================== WORKED SETS =====================

def rebuild_worked_sets():
    """Rebuild worked chart codes from cached chart, then print stats."""
    global worked_chart_codes, worked_2026_codes

    # Chart (lifetime worked) — from cache file
    if os.path.exists(CHART_CACHE):
        with open(CHART_CACHE) as f:
            data = json.load(f)
        codes = set()
        for code_str, bands in data.items():
            if isinstance(bands, dict):
                for band, status in bands.items():
                    if status in (1, 2, 3, True):
                        try:
                            codes.add(str(int(code_str)))
                        except ValueError:
                            pass
                        break
        worked_chart_codes = codes

    # Stats
    chart_codes = worked_chart_codes
    not_2026 = chart_codes - worked_2026_codes  # chart: str codes; 2026: str codes
    all_known_str = set(str(c) for c in entity_codes.values())
    never = all_known_str - chart_codes

    print(f"  → {len(chart_codes)} entitats treballades (lifetime)")
    print(f"  → {len(not_2026)} treballades abans, NOU el {FILTER_YEAR}")
    print(f"  → {len(never)} entitats mai treballades")


# ===================== SPOT PROCESSING =====================

def process_spot(line):
    match = SPOT_RE.search(line)
    if not match:
        return
    spotter = match.group(1).upper()
    freq = float(match.group(2))
    dx_call = match.group(3).upper()
    comment = match.group(4)

    mode = guess_mode(freq, comment)

    # CW always ignored
    if mode == "CW":
        return

    # Frequency range filter
    if freq < ARGS.freq_min or freq > ARGS.freq_max:
        return

    # Mode filter (ALL = all modes)
    if ARGS.modes != "ALL" and mode not in set(m.strip() for m in ARGS.modes.split(",")):
        return

    entity = lookup_entity(dx_call)

    # Resolve to DXCC code
    code = entity_to_code(entity)
    if not code:
        # Fallback: Club Log API (rare)
        code = clublog_lookup_api(dx_call)
        if not code:
            print(f"⚠️ No s'ha pogut resoldre {dx_call} → {entity} (sense codi DXCC)")
            return

    # === TWO-TIER ALERTING ===
    in_chart = code in worked_chart_codes      # Worked ever?
    in_2026 = code in worked_2026_codes         # Worked this year?

    if in_2026:
        return  # Already worked this year → silent

    is_never = not in_chart  # Never worked

    if not is_never:
        # Worked before, NOT in 2026 → daytime only
        if not is_daytime():
            return

    # === ALERT ===
    now = time.time()
    key = (code,)
    last = last_alert_time.get(key, 0)
    hours_since = (now - last) / 3600

    if last != 0 and hours_since < REALERT_HOURS:
        old_freq = last_freq.get(key, 0)
        is_freq_change = abs(freq - old_freq) > 0.1
        if not is_freq_change:
            return  # Already alerted recently, no QSY

    last_alert_time[key] = now
    last_freq[key] = freq

    re_text = ""
    if last != 0:
        mins = int((now - last) / 60)
        old_freq = last_freq.get(key, 0)
        if abs(freq - old_freq) > 0.1:
            re_text = f" (QSY! era {old_freq} kHz)"
        else:
            re_text = f" (Nou avís, fa {mins} min)"

    if is_never:
        alert_type = "🚨 MAI TREBALLAT"
        prefix = "🚨"
    else:
        alert_type = f"🌅 NOU el {FILTER_YEAR}"
        prefix = "🌅"

    mode_display = f" | {mode}" if mode != "UNKNOWN" else ""
    msg = (
        f"{prefix} {dx_call} → {entity} (code {code})\n"
        f"📻 {freq} kHz{mode_display}\n"
        f"📢 {spotter}\n"
        f"{alert_type}{re_text}"
    )
    print(msg)
    send_telegram(msg)


# ===================== TELNET CLIENT =====================

def cluster_loop():
    """Maintains a persistent Telnet connection to the DX Cluster."""
    while True:
        try:
            print(f"Connecting to {ARGS.cluster_host}:{ARGS.cluster_port}...")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(120)
                s.connect((ARGS.cluster_host, ARGS.cluster_port))
                login_call = ARGS.cluster_login or ARGS.callsign
                s.sendall(f"{login_call}\n".encode())
                # Login DXSpider (obligatori per rebre spots)
                time.sleep(1)
                s.sendall(b"set/name LaIA\n")
                time.sleep(0.5)
                s.sendall(b"set/qth Lleida\n")
                time.sleep(0.5)
                s.sendall(b"set/qra JN01\n")
                time.sleep(0.5)
                s.sendall(b"set/homenode none\n")
                # Drenar buffer de login
                s.settimeout(2)
                try:
                    while True:
                        d = s.recv(65536)
                        if not d: break
                except socket.timeout:
                    pass
                s.settimeout(120)
                buffer = ""
                while True:
                    data = s.recv(4096)
                    if not data:
                        break
                    buffer += data.decode("utf-8", errors="ignore")
                    lines = buffer.split("\n")
                    buffer = lines.pop()
                    for line in lines:
                        if line.strip():
                            process_spot(line.strip())
        except Exception as e:
            print(f"Connection lost ({e}). Reconnecting in 10s...")
            time.sleep(10)


# ===================== PERIODIC REFRESH =====================

def refresh_prefix_map():
    """Downloads cty.dat and regenerates dxcc_prefixes.json."""
    global dxcc_prefixes, sorted_prefixes, dxcc_exact, dxcc_excludes
    print("[CTY] Downloading and regenerating prefix map...")
    try:
        script = os.path.join(WORKSPACE, "parse_cty.py")
        result = subprocess.run(["python3", script], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            with open(PREFIX_FILE) as f:
                data = json.load(f)
            dxcc_prefixes = data["map"]
            sorted_prefixes = data["prefixes"]
            dxcc_exact = data.get("exact", {})
            dxcc_excludes = data.get("excludes", {})
            dxcc_entities[:] = data.get("dxcc_entities", [])
            region_map.clear()
            region_map.update(data.get("region_map", {}))
            print(f"[CTY] Prefix map updated: {len(dxcc_prefixes)} prefixes, "
                  f"{len(dxcc_exact)} exceptions, {len(dxcc_entities)} DXCC entities")
            return True
        else:
            print(f"[CTY] Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"[CTY] Error: {e}")
        return False


def clublog_refresh_loop():
    """Refreshes Club Log chart every 24h."""
    while True:
        clublog_download_chart()
        rebuild_worked_sets()
        time.sleep(86400)


def cty_refresh_loop():
    """Refreshes cty.dat / prefix map every 24h."""
    while True:
        refresh_prefix_map()
        time.sleep(86400)


def adif_refresh_loop():
    """Downloads fresh ADIF from eQSL every 24h."""
    while True:
        if ARGS.eqsl_user and ARGS.eqsl_pass:
            download_adif_from_eqsl()
            if ARGS.adif:
                load_adif_2026(os.path.abspath(ARGS.adif))
            rebuild_worked_sets()
        time.sleep(86400)


# ===================== MAIN =====================

if __name__ == "__main__":
    ARGS = parse_args()
    callsign_display = ARGS.callsign.upper()
    print(f"{'='*60}")
    print(f"  DXCC Club Log Monitor — {callsign_display}")
    print(f"  Modes: {ARGS.modes}  Freq: {ARGS.freq_min}-{ARGS.freq_max} kHz")
    print(f"  Alerta 24/7: entitats MAI treballades")
    print(f"  Alerta diürna: entitats NO treballades el {ARGS.year} (7:00-23:00)")
    print(f"{'='*60}")

    if not ARGS.telegram_token:
        print("⚠️  Telegram not configured.")

    # Load prefix map
    load_prefix_map()
    print(f"Prefix map: {len(dxcc_prefixes)} prefixes")

    # Load entity codes
    load_entity_codes()
    print(f"Entity codes: {len(entity_codes)}")

    # Load ADIF 2026 (if provided)
    if ARGS.adif:
        load_adif_2026(os.path.abspath(ARGS.adif))

    # Download Club Log chart
    clublog_download_chart()

    # Download fresh ADIF from eQSL (if credentials configured)
    if ARGS.eqsl_user and ARGS.eqsl_pass:
        download_adif_from_eqsl()
        if ARGS.adif:
            load_adif_2026(os.path.abspath(ARGS.adif))

    rebuild_worked_sets()

    # Background refresh threads
    t_clublog = threading.Thread(target=clublog_refresh_loop, daemon=True)
    t_clublog.start()

    t_cty = threading.Thread(target=cty_refresh_loop, daemon=True)
    t_cty.start()

    if ARGS.eqsl_user and ARGS.eqsl_pass:
        t_adif = threading.Thread(target=adif_refresh_loop, daemon=True)
        t_adif.start()

    time.sleep(2)

    print("Spots entrants (Ctrl+C per sortir):")
    cluster_loop()
