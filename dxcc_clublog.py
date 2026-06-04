#!/usr/bin/env python3
"""
dxcc_clublog.py — DXCC monitor (entitats per codi numèric)

Dos nivells d'alerta:
  🚨 MAI TREBALLAT → 24/7 (entitat NO al chart de Club Log)
  🌅 NO EL 2026 → només de dia (entitat treballada abans, NO enguany)

Refresh diari (24h): cty.dat, Club Log chart, ADIF 2026
"""
import socket, re, json, time, os, argparse, requests, threading, logging, sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────
WORKSPACE = Path(__file__).resolve().parent
PREFIX_FILE = WORKSPACE / "dxcc_prefixes.json"
ENTITY_CODES_FILE = WORKSPACE / "entity_codes.json"
CLUBLOG_CHART_FILE = WORKSPACE / "clublog_dxcc_chart.json"
CLUBLOG_CACHE_FILE = WORKSPACE / "clublog_entity_cache.json"
CTY_FILE = WORKSPACE / "cty.dat"
CLUBLOG_DXCC_URL = "https://clublog.org/dxcc"
CLUBLOG_CHART_URL = "https://clublog.org/json_dxccchart.php"
CTY_URL = "https://www.country-files.com/cty/cty.dat"

# ── Constants ──────────────────────────────────────────
# Duu formats: "DX de SPOTTER: FREQ DX_CALL..." I "  FREQ DX_CALL   DATE   COMM   <SPOTTER>"
SPOT_RE = re.compile(r"(?:^DX\s+de\s+(\S+):)?\s*([0-9.]+)\s+([A-Z0-9/]+)(.*?)(?:<(\S+)>)?$", re.IGNORECASE)
DAY_START = 7   # 07:00
DAY_END   = 23  # 23:00
CACHE_TTL = 86400
REALERT_HOURS = 2

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("dxcc")


# ═══════════════════════════════════════════════════════
# GLOBALS
# ═══════════════════════════════════════════════════════

ARGS = None
worked_codes = set()       # entity CODES → lifetime (chart clublog)
worked_2026 = set()        # entity CODES → treballades el 2026 (ADIF)
name_to_code = {}          # entity NAME → code (ARRL)
prefix_data = {}           # mutable dict (thread-safe)
prefix_lock = threading.Lock()
last_alert = {}            # throttle { (code, mode): timestamp }
alert_count = 0
spot_count = 0
clublog_fallbacks = 0
clublog_cache = {}


# ═══════════════════════════════════════════════════════
# 1. PREFIX MAP (cty.dat)
# ═══════════════════════════════════════════════════════

def load_prefix_map():
    if not PREFIX_FILE.exists():
        log.error(f"Falta {PREFIX_FILE}"); exit(1)
    with open(PREFIX_FILE) as f: return json.load(f)


def rebuild_prefix_map():
    log.info("📡 cty.dat ...")
    try:
        urllib.request.urlretrieve(CTY_URL, CTY_FILE)
        with open(CTY_FILE, encoding="latin-1") as f: raw = f.read()
        lines = raw.replace("\r\n", "\n").split("\n")
        mapping, exact_map, excludes = {}, {}, {}
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.strip(): i += 1; continue
            if ":" in line and line.count(":") >= 7:
                parts = line.split(":")
                en = parts[0].strip()
                ne = [p for p in parts[1:] if p.strip()]
                pp = ne[-1].strip().upper() if ne else ""
                if pp: mapping[pp] = en
                i += 1; pb = ""
                while i < len(lines):
                    n = lines[i]
                    if not n.strip(): i += 1; break
                    if n.count(":") >= 7: break
                    pb += n.strip(); i += 1
                pb = pb.rstrip(";")
                for p in pb.split(","):
                    p = p.strip()
                    if not p: continue
                    if p.startswith("="):
                        m = re.match(r"^=([A-Z0-9/]+)", p[1:])
                        if m:
                            c = m.group(1)
                            idx = re.search(r"\((\d+)\)", p)
                            cd = re.search(r"\[(\d+)\]", p)
                            if idx and not cd: excludes[c] = pp
                            else: exact_map[c] = en
                    else:
                        p = re.sub(r"[\(\[].*?[\)\]]", "", p).strip()
                        if p: mapping[p] = en
                continue
            i += 1
        sp = sorted(mapping.keys(), key=lambda x: (-len(x), x))
        ae = sorted(set(mapping.values()))
        data = {"prefixes": sp, "map": mapping,
                "exact": exact_map, "excludes": excludes,
                "dxcc_entities": ae}
        with open(PREFIX_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False)
        log.info(f"  ✓ {len(mapping)} prefixes, {len(exact_map)} excepcions, {len(ae)} entitats")
        return data
    except Exception as e:
        log.error(f"  ✗ cty.dat: {e}")
        return None


def entity_from_prefix(cs, pd):
    p = pd["map"]; sp = pd["prefixes"]
    e = pd.get("exact", {}); x = pd.get("excludes", {})
    r = cs.upper(); b = r.replace("/", " ").split()[0]
    if r in e: return e[r]
    if b in e: return e[b]
    if "/" in r:
        sf = r.split("/")[-1]
        if sf in p: return p[sf]
        bl, best = 0, None
        for pf in sp:
            if sf.startswith(pf) and len(pf) > bl: bl, best = len(pf), p[pf]
        if best: return best
    bl, best = 0, "UNKNOWN"
    for pf in sp:
        if r.replace("/", " ").startswith(pf) and len(pf) > bl:
            if x.get(b) == pf: continue
            bl, best = len(pf), p[pf]
    return best


# ═══════════════════════════════════════════════════════
# 2. ENTITY CODES
# ═══════════════════════════════════════════════════════

def load_entity_codes():
    global name_to_code
    if not ENTITY_CODES_FILE.exists():
        log.error(f"Falta {ENTITY_CODES_FILE}"); exit(1)
    with open(ENTITY_CODES_FILE) as f: name_to_code = json.load(f)
    log.info(f"Entity codes: {len(name_to_code)}")


def code_from_entity(name):
    return name_to_code.get(name.upper(), 0)


# ═══════════════════════════════════════════════════════
# 3. ADIF 2026
# ═══════════════════════════════════════════════════════

def build_worked_2026(adif_path):
    """Parsejar ADIF i extreure codis d'entitats treballades el 2026."""
    global worked_2026
    worked_2026.clear()
    if not adif_path or not Path(adif_path).exists():
        log.warning(f"⚠️  No ADIF: {adif_path}")
        return
    log.info("📄 ADIF 2026...")
    with open(adif_path, errors="ignore") as f: content = f.read()
    pd_data = prefix_data
    codes = set()
    for m in re.finditer(r'<QSO_DATE:\d+:\w+>(\d+).*?<CALL:\d+>([^<]+)', content, re.DOTALL):
        date = m.group(1)
        call = m.group(2).strip().upper()
        if date >= "20260101":
            en = entity_from_prefix(call, pd_data)
            if en != "UNKNOWN":
                c = code_from_entity(en)
                if c: codes.add(c)
    worked_2026 = codes
    log.info(f"  ✓ {len(codes)} entitats treballades el 2026")


# ═══════════════════════════════════════════════════════
# 4. CLUB LOG CHART
# ═══════════════════════════════════════════════════════

def fetch_chart():
    url = (f"{CLUBLOG_CHART_URL}?call={ARGS.callsign}&api={ARGS.clublog_api_key}"
           f"&email={ARGS.clublog_email}&password={ARGS.clublog_password}"
           f"&mode=0&date=0")
    log.info("📡 Club Log chart...")
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            d = r.json()
            with open(CLUBLOG_CHART_FILE, "w") as f: json.dump(d, f)
            log.info(f"  ✓ {len(d)} entitats")
            return d
        log.error(f"  ✗ HTTP {r.status_code}"); return None
    except Exception as e:
        log.error(f"  ✗ {e}"); return None


def load_worked_set():
    global worked_codes
    worked_codes.clear()
    chart = None
    if ARGS.clublog_email and ARGS.clublog_password:
        chart = fetch_chart()
    if not chart and CLUBLOG_CHART_FILE.exists():
        log.info("Chart en cache...")
        with open(CLUBLOG_CHART_FILE) as f: chart = json.load(f)
    if isinstance(chart, dict):
        for cs, bands in chart.items():
            if isinstance(bands, dict):
                for b, s in bands.items():
                    if s in (1, 2, 3, True):
                        worked_codes.add(int(cs)); break
        log.info(f"  → {len(worked_codes)} entitats treballades (lifetime)")
        not_in_2026 = worked_codes - worked_2026
        log.info(f"  → {len(not_in_2026)} treballades abans, NO el 2026")
        log.info(f"  → {340 - len(worked_codes)} entitats mai treballades")
    else:
        log.warning("⚠️  Sense chart — TOTS els spots = NOUS!")


# ═══════════════════════════════════════════════════════
# 5. CLUB LOG FALLBACK
# ═══════════════════════════════════════════════════════

def resolve_clublog(callsign):
    global clublog_fallbacks
    if callsign in clublog_cache:
        e = clublog_cache[callsign]
        if time.time() - e["ts"] < CACHE_TTL: return e["name"], e["code"]
    url = f"{CLUBLOG_DXCC_URL}?call={callsign}&full=1&api={ARGS.clublog_api_key}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            d = r.json()
            n = d.get("Name", None); c = d.get("DXCC", 0)
            if n and c and 1 <= c <= 999:
                clublog_cache[callsign] = {"name": n, "code": c, "ts": time.time()}
                clublog_fallbacks += 1
                return n, c
    except: pass
    return None, 0


# ═══════════════════════════════════════════════════════
# 6. MODE + HOUR CHECK
# ═══════════════════════════════════════════════════════

def guess_mode(freq, comment):
    c = comment.upper()
    if "FT8" in c: return "FT8"
    if "FT4" in c: return "FT4"
    if "CW" in c: return "CW"
    if "SSB" in c: return "SSB"
    if "RTTY" in c: return "RTTY"
    if "DIGI" in c: return "DIGI"
    if 14000 <= freq <= 14070 or 21000 <= freq <= 21070: return "CW"
    if 7000 <= freq <= 7040: return "CW"
    if (7074 <= freq <= 7076) or (14074 <= freq <= 14076): return "FT8"
    if 14100 <= freq <= 14350: return "SSB"
    return "UNKNOWN"


def is_daytime():
    h = datetime.now().hour
    return DAY_START <= h < DAY_END


# ═══════════════════════════════════════════════════════
# 7. TELEGRAM
# ═══════════════════════════════════════════════════════

def tg(msg):
    if not ARGS.telegram_token: return
    try:
        requests.post(f"https://api.telegram.org/bot{ARGS.telegram_token}/sendMessage",
                      json={"chat_id": ARGS.telegram_chat_id, "text": msg,
                            "parse_mode": "Markdown"}, timeout=5)
    except: pass


# ═══════════════════════════════════════════════════════
# 8. SPOT PROCESSING
# ═══════════════════════════════════════════════════════

def process(line):
    global alert_count, spot_count
    m = SPOT_RE.search(line)
    if not m: return
    # Spotter pot venir de "DX de SPOTTER:" (grup 1) o "<SPOTTER>" final (grup 5)
    spotter = (m.group(1) or m.group(5) or "?").upper()
    f = float(m.group(2)) * 1000
    dx = m.group(3).upper()
    rest = m.group(4).strip()
    if f < ARGS.freq_min or f > ARGS.freq_max: return
    spot_count += 1

    with prefix_lock:
        pd = prefix_data

    ename = entity_from_prefix(dx, pd)
    fallback = False
    ecode = code_from_entity(ename) if ename != "UNKNOWN" else 0

    if ename == "UNKNOWN" and ARGS.clublog_api_key:
        rn, rc = resolve_clublog(dx)
        if rn: ename = rn; ecode = rc; fallback = True

    if ename == "UNKNOWN" or ecode == 0: return

    mode = guess_mode(f, rest)
    wanted = [x.strip().upper() for x in ARGS.modes.split(",")]
    if mode not in wanted and "ALL" not in wanted: return

    # ── Determine alert tier ──
    never_worked = ecode not in worked_codes      # NO al chart = mai treballat
    not_2026 = ecode in worked_codes and ecode not in worked_2026
    worked_now = ecode in worked_2026

    if worked_now: return  # Ja treballat enguany

    # Si mai treballat → alerta 24/7
    # Si treballat abans NO el 2026 → alerta només de dia
    if not_2026 and not is_daytime(): return  # Nit, silenci

    # Throttle
    k = (ecode, mode); now = time.time()
    if k in last_alert and (now - last_alert[k]) < REALERT_HOURS * 3600: return
    last_alert[k] = now

    alert_count += 1
    fm = f"{f/1000:.1f}" if f >= 1000 else f"{f/1000:.3f}"

    if never_worked:
        suf = " 🚨 MAI TREBALLAT"
    else:
        suf = " 🌅 NO el 2026"

    tg_suf = " 🔍" if fallback else suf
    msg = (f"**#{alert_count} — {ename}**{tg_suf}\n"
           f"**{dx}** {fm} MHz {mode}\n"
           f"Code #{ecode} — {datetime.now().strftime('%H:%M UTC')} — {spotter}")
    if never_worked: msg += "\n_Alerta 24/7: entitat mai treballada!_"
    elif not_2026: msg += "\n_Alerta diürna: entitat no treballada el 2026_"

    log.info(f"  {datetime.now().strftime('%H:%M:%S')} | {dx:10s} | {fm:>7s} | "
             f"{mode:4s} | #{ecode} {ename}{' 🚨' if never_worked else ' 🌅' if not_2026 else ''}")
    tg(msg)


# ═══════════════════════════════════════════════════════
# 9. CLUSTER
# ═══════════════════════════════════════════════════════

def cluster_loop():
    while True:
        try:
            log.info(f"→ {ARGS.cluster_host}:{ARGS.cluster_port}...")
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
                log.info("Login complet — escoltant spots...")
                s.settimeout(120)
                buf = ""
                while True:
                    data = s.recv(4096)
                    if not data: break
                    buf += data.decode("utf-8", errors="ignore")
                    lines = buf.split("\n"); buf = lines.pop()
                    for line in lines:
                        if line.strip(): process(line.strip())
        except Exception as e:
            log.warning(f"↻ {e}. Reconnectant en 10s...")
            time.sleep(10)


# ═══════════════════════════════════════════════════════
# 10. MAINTENANCE
# ═══════════════════════════════════════════════════════

def save_cache():
    if ARGS.clublog_api_key and clublog_cache:
        with open(CLUBLOG_CACHE_FILE, "w") as f: json.dump(clublog_cache, f)


def load_cache():
    if CLUBLOG_CACHE_FILE.exists():
        with open(CLUBLOG_CACHE_FILE) as f: clublog_cache.update(json.load(f))
        log.info(f"Cache: {len(clublog_cache)} callsigns")


def daily_refresh():
    while True:
        time.sleep(86400)
        log.info("🔄 Refresh diari...")
        log.info("  ╔══ cty.dat ══")
        nd = rebuild_prefix_map()
        if nd:
            with prefix_lock: prefix_data.clear(); prefix_data.update(nd)
            log.info("  ╚══ prefix map actualitzat")
        else:
            log.warning("  ╚══ cty.dat NO actualitzat")
        log.info("  ╔══ Club Log Chart ══")
        ch = fetch_chart()
        if ch: load_worked_set()
        log.info("  ╚══ chart actualitzat")
        if ARGS.adif:
            log.info("  ╔══ ADIF 2026 ══")
            build_worked_2026(ARGS.adif)
            log.info("  ╚══ 2026 actualitzat")


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main():
    global ARGS, prefix_data
    p = argparse.ArgumentParser(description="DXCC Club Log Monitor")
    p.add_argument("--callsign", required=True)
    p.add_argument("--cluster-login", help="Callsign per login al cluster")
    p.add_argument("--clublog-api-key")
    p.add_argument("--clublog-email")
    p.add_argument("--clublog-password")
    p.add_argument("--telegram-token")
    p.add_argument("--telegram-chat-id")
    p.add_argument("--adif", help="Fitxer ADIF per entitats 2026")
    p.add_argument("--modes", "-m", default="SSB")
    p.add_argument("--freq-min", type=float, default=3000)
    p.add_argument("--freq-max", type=float, default=55000)
    p.add_argument("--cluster-host", default="dxc.pi4cc.nl")
    p.add_argument("--cluster-port", type=int, default=8000)
    ARGS = p.parse_args()

    print(f"{'='*60}")
    print(f"  DXCC Club Log Monitor — {ARGS.callsign.upper()}")
    print(f"  Modes: {ARGS.modes}  Freq: {ARGS.freq_min}-{ARGS.freq_max} kHz")
    print(f"  Alerta 24/7: entitats MAI treballades")
    print(f"  Alerta diürna: entitats NO treballades el 2026 ({DAY_START}:00-{DAY_END}:00)")
    print(f"  Prefix map: cty.dat | Treballades: Club Log + ADIF 2026")
    print(f"{'='*60}")

    pd = load_prefix_map()
    prefix_data.update(pd)
    log.info(f"Prefix map: {len(pd['map'])} prefixes")
    load_entity_codes()
    if ARGS.clublog_api_key: load_cache()
    build_worked_2026(ARGS.adif)
    load_worked_set()

    if not ARGS.telegram_token:
        log.warning("⚠️  Sense Telegram — alertes només per consola")

    def cache_loop():
        while True: time.sleep(300); save_cache()
    threading.Thread(target=cache_loop, daemon=True).start()

    if ARGS.clublog_email:
        threading.Thread(target=daily_refresh, daemon=True).start()

    time.sleep(1)
    print(f"Spots entrants (Ctrl+C per sortir):")
    cluster_loop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        save_cache()
        print("\nAturat.")
