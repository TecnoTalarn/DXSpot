#!/usr/bin/env python3
"""
parse_cty.py — Converteix cty.dat a dxcc_prefixes.json (prefix → entity_name)
Inclou excepcions (=CALLSIGN) del cty.dat per a callsigns especiífics.
Executar: python3 parse_cty.py
Descàrrega automàtica de https://www.country-files.com/cty/cty.dat
"""

import re, json, os, urllib.request

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
CTY_PATH = os.path.join(WORKSPACE, "cty.dat")
OUT_PATH = os.path.join(WORKSPACE, "dxcc_prefixes.json")
CTY_URL = "https://www.country-files.com/cty/cty.dat"

def download():
    print("Descarregant cty.dat...")
    urllib.request.urlretrieve(CTY_URL, CTY_PATH)
    print("OK")

# Entitats sub-regionals que NO són DXCC individuals (es normalitzen al seu pare)
# Font: ARRL DXCC Current Entities (340 entitats vàlides)
REGION_MAP = {
    # Estats Units
    "Alaska": "United States",
    "Hawaii": "United States",
    # Regne Unit
    "England": "United Kingdom",
    "Scotland": "United Kingdom",
    "Wales": "United Kingdom",
    "Northern Ireland": "United Kingdom",
    "Shetland Islands": "United Kingdom",
    # Rússia
    "European Russia": "Russia",
    "Asiatic Russia": "Russia",
    "Kaliningrad": "Russia",
    # Turquia
    "European Turkey": "Turkey",
    "Asiatic Turkey": "Turkey",
    # Malàisia
    "East Malaysia": "Malaysia",
    "West Malaysia": "Malaysia",
    # Itàlia
    "Sicily": "Italy",
    "Sardinia": "Italy",
    # Grècia
    "Crete": "Greece",
    "Dodecanese": "Greece",
    # França
    "Corsica": "France",
    # Espanya
    "Balearic Islands": "Spain",
    "Canary Islands": "Spain",
    "Ceuta & Melilla": "Spain",
}

# Entitats a EXCLOURE del compte DXCC
# (només entitats realment eliminades o que no són DXCC individuals)
DELETED_ENTITIES = {
    "African Italy",      # NO era una entitat DXCC (era un modifier sota Italy)
    "Bear Island",        # Part de Svalbard (JW), no entitat ARRL separada
    "Shetland Islands",   # Part d'Escòcia (GM), no entitat ARRL separada
    "Sicily",             # Part d'Itàlia (IT9), no entitat ARRL separada
    "Vienna Intl Ctr",    # NO reconeguda al llistat ARRL 2022
}

# Noms d'entitat a fusionar sota un nom ARRL únic
# (cty.dat les separa per regió però ARRL les tracta com una)
MERGED_ENTITY_NAMES = {
    "European Turkey": "Turkey",
    "Asiatic Turkey": "Turkey",
}

def parse():
    with open(CTY_PATH, encoding="latin-1") as f:
        raw = f.read()

    # Normalitzar CRLF -> LF i separar per línies
    lines = raw.replace("\r\n", "\n").split("\n")

    mapping = {}      # Prefix -> entity_name
    exact_map = {}    # Callsign exacte -> entity_name (per a excepcions =CALLSIGN amb codi DXCC)
    excludes = {}     # callsign -> prefix_to_skip (excloure només d'un prefix específic)

    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        if ":" in line:
            colon_count = line.count(":")
            if colon_count >= 7:
                parts = line.split(":")
                entity_name = parts[0].strip()
                # Aplicar fusió de noms (ex: European Turkey → Turkey)
                if entity_name in MERGED_ENTITY_NAMES:
                    merged = MERGED_ENTITY_NAMES[entity_name]
                    entity_name = merged
                # El prefix principal és l'última part NO buida
                non_empty = [p for p in parts[1:] if p.strip()]
                primary_prefix = non_empty[-1].strip().upper() if non_empty else ""
                if primary_prefix:
                    mapping[primary_prefix] = entity_name

                i += 1
                prefix_buffer = ""
                while i < len(lines):
                    next_line = lines[i]
                    if not next_line.strip():
                        i += 1
                        break
                    if next_line.count(":") >= 7:
                        break
                    prefix_buffer += next_line.strip()
                    i += 1

                prefix_buffer = prefix_buffer.rstrip(";")
                for p in prefix_buffer.split(","):
                    p = p.strip()
                    if not p:
                        continue

                    # Detectar excepció (=CALLSIGN)
                    if p.startswith("="):
                        p_clean = p.lstrip("=")
                        match = re.match(r'^([A-Z0-9/]+)', p_clean)
                        if match:
                            call = match.group(1)
                            # Format =CALLSIGN -> excepció, assignar a l'entitat
                            # Format =CALLSIGN(idx)[code] -> excepció amb codi DXCC
                            # Format =CALLSIGN(idx) -> exclusió del prefix, no pertany a l'entitat
                            prefix_idx = re.search(r'\((\d+)\)', p)
                            dxcc_code = re.search(r'\[(\d+)\]', p)
                            if prefix_idx and not dxcc_code:
                                # =CALLSIGN(idx) sense [code]: només excloure del prefix
                                excludes[call] = primary_prefix
                            else:
                                # Amb [code] o sense parentesis: assignar a l'entitat
                                exact_map[call] = entity_name
                    else:
                        p = re.sub(r"[\(\[].*?[\)\]]", "", p).strip()
                        if p:
                            mapping[p] = entity_name
                continue
        i += 1

    # Correccions manuals — entitats que NO són DXCC vàlids a ARRL
    MANUAL_FIXES = {
        "IG9": "Italy",   # African Italy — no és entitat DXCC separada
        "IH9": "Italy",   # African Italy — no és entitat DXCC separada
    }
    for prefix, entity in MANUAL_FIXES.items():
        if prefix in mapping:
            old = mapping[prefix]
            mapping[prefix] = entity
            print(f"  ⚠ {prefix}: {old} -> {entity} (correcció manual)")

    # Correccions d'indicatius complets — override de cty.dat erroni
    MANUAL_CALLSIGN_FIXES = {
        "VP8/SQ1SGB": "Antarctica",  # cty.dat diu South Sandwich, però QRZ diu Antàrtida (Halley VI)
        "KG4JOK": "United States",    # USA Navy, no Guantanamo
        "KG4BLR": "United States",    # USA Navy, no Guantanamo
        "KG4YJS": "United States",    # USA Navy, no Guantanamo
        "KG4AKV": "United States",    # USA Navy, no Guantanamo
        "KG4VCF": "United States",    # Validat per Jordi
        "3Y0K": "Bouvet",               # 3Y0K = DXpedició Bouvet 2026
        "LZ0A": "South Shetland Islands",  # Base búlgara a Antàrtida (Livingston)
        "KH7AL/KH9": "Wake Island",     # Portable des de Wake
        "SV1GA/A": "Mount Athos",        # SV amb /A = Mount Athos
        "FO/F4LYI": "Marquesas Islands",  # FO portable Marquesas
        "3D2V": "Rotuma Island",         # 3D2 Rotuma (no Fiji)
        "E51JAN": "North Cook Islands",  # E5 North Cook (no South)
        "K8K": "American Samoa",          # K8K DXpedition KH8 2024
        "W8S": "Swains Island",            # W8S DXpedition KH8/s 2023
        "N5J": "Palmyra & Jarvis Islands", # N5J DXpedition KH5 2024
    }
    for call, entity in MANUAL_CALLSIGN_FIXES.items():
        exact_map[call] = entity
        print(f"  ⚠ {call}: override manual -> {entity}")

    sorted_prefixes = sorted(mapping.keys(), key=lambda x: (-len(x), x))
    
    # Normalitzar entitats: aplicar DELETED_ENTITIES (NO region_map — 340 ARRL)
    all_entities = set(mapping.values())
    dxcc_entities = set()
    for e in all_entities:
        if e in DELETED_ENTITIES:
            print(f"  ⏭ {e} -> exclòs (deleted/admin)")
            continue
        # Mantenir totes les entitats raw (340 ARRL), incloent sub-regions
        dxcc_entities.add(e)
    
    data = {
        "prefixes": sorted_prefixes,
        "map": mapping,
        "exact": exact_map,
        "excludes": excludes,  # {callsign: prefix_to_skip}
        "region_map": REGION_MAP,  # sub-regió -> parent DXCC
        "deleted_entities": list(DELETED_ENTITIES),
        "dxcc_entities": sorted(dxcc_entities),  # llista de les ~340 vàlides
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Generat {OUT_PATH}: {len(mapping)} prefixes, {len(exact_map)} excepcions, {len(excludes)} exclosos, {len(all_entities)} entitats raw, {len(dxcc_entities)} entitats DXCC vàlides")
    return data

def lookup_test(data, callsign):
    """Test prefix matching amb excepcions."""
    cs = callsign.upper()
    # 1. Comprovar match exacte
    exact = data.get("exact", {})
    if cs in exact:
        return exact[cs]
    # 2. Prefix matching (saltant exclòs del seu prefix concret)
    excludes = data.get("excludes", {})
    best = ("", "UNKNOWN")
    for p in data.get("prefixes", []):
        if cs.startswith(p) and len(p) > len(best[0]):
            # Només saltar si l'exclusió és per a aquest prefix
            if excludes.get(cs) != p:
                best = (p, data["map"][p])
    return best[1]

if __name__ == "__main__":
    download()
    data = parse()
    tests = [
        "EA3XYZ", "F1ABC", "K1ABC", "KG4VET", "KG4AB",
        "KG4V", "KG4BIG", "KG4STL", "KG4NE",
        "3Y0X", "3D2CCC", "4U0ITU"
    ]
    print("\nTests:")
    for t in tests:
        print(f"  {t} -> {lookup_test(data, t)}")
