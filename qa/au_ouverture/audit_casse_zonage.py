"""Point 2 de l'ARBITRAGE RE-RUN (Vic) — AUDIT de normalisation du matching zonage.

Question : combien de zones du SIG ne matchent AUCUNE règle de calibration (plu_<commune>.yaml lu par
`resolve_zone`), tous types (U/A/N/AU), et pour quelle cause NORMALISABLE (casse, espaces, tirets,
accents, variantes) ? Combien de parcelles SERVIES en dépendent ?

RAPPORT SEUL — aucune correction ici (Vic : « rapporter avant de corriger »). Read-only.

Le matcher visé est `resolve_zone` : match EXACT `code in rules` (sensible à la casse), puis AU*st
(regex sensible à la casse), puis renvoi AU<n>→U<n>, sinon estimation générique (calibree=False).
Une zone qui tombe en générique alors qu'une clé du YAML lui correspondrait APRÈS normalisation =
perte silencieuse de calibration.
"""
import os, re, sys, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
import yaml
from sqlalchemy import text
from labuse.db import session_scope
from labuse.faisabilite.plu_rules import _commune_slug, _CONFIG_DIR

SERVED_RUN = "q_v7_defisc"

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", s.lower())

def cause(zl: str, key: str) -> str:
    if zl == key:
        return "exact"
    if zl.lower() == key.lower():
        return "casse"
    if re.sub(r"[\s\-]", "", zl).lower() == re.sub(r"[\s\-]", "", key).lower():
        return "espaces/tirets"
    if norm(zl) == norm(key):
        return "accents/variantes"
    return "?"

def yaml_for(commune):
    p = _CONFIG_DIR / f"plu_{_commune_slug(commune)}.yaml"
    if not p.is_file():
        return None
    return yaml.safe_load(p.read_text(encoding="utf-8"))

def match_kind(zl, keys, st_liste):
    """Reproduit la logique de resolve_zone : renvoie (matched_calibree, kind)."""
    if zl in keys:
        return True, "exact"
    if zl in st_liste or re.fullmatch(r"AU\w*st", zl):
        return True, "au_st"
    m = re.fullmatch(r"AU(\d[a-zA-Z0-9]*)", zl)
    if m and ("U" + m.group(1)) in keys:
        return True, "renvoi"
    return False, "generique"

def rescue(zl, keys, st_liste):
    """Une normalisation (casse/espaces/tirets/accents) sauverait-elle ce zl ? Renvoie (clé, cause)."""
    nz = norm(zl)
    for k in keys:
        if norm(k) == nz:
            return k, cause(zl, k)
    # AU*st normalisé (ex. 'AU1ST' / 'au1st')
    if re.fullmatch(r"au\w*st", nz) and not (zl in st_liste or re.fullmatch(r"AU\w*st", zl)):
        return "AU*st", "casse"
    m = re.fullmatch(r"au(\d[a-z0-9]*)", nz)
    if m:
        for k in keys:
            if norm(k) == norm("U" + m.group(1)):
                return k, "casse/renvoi"
    return None, None

with session_scope() as s:
    communes = s.execute(text("""
        SELECT substring(idu from 1 for 5) insee, commune FROM parcels
        GROUP BY 1,2 ORDER BY 1""")).all()

    tot_def_zones = tot_def_parc = tot_def_served = 0
    print(f"{'commune':22s} {'zones':>5s} {'nomatch':>7s} {'DÉFAUT':>6s} {'parc':>6s} {'servies':>7s}")
    detail = []
    for insee, commune in communes:
        doc = yaml_for(commune)
        # zones SIG de la commune + comptes (total et servies = non ecartee dans le run servi)
        zl_rows = s.execute(text("""
            SELECT z.zone_lib,
                   count(*) AS n,
                   count(*) FILTER (WHERE sc.tier IS NOT NULL AND sc.tier <> 'ecartee') AS servies
            FROM parcels p JOIN parcel_zone_plu z ON z.idu = p.idu
            LEFT JOIN parcel_p_score_v2 sc ON sc.parcelle_id = p.idu AND sc.run_id = :run
            WHERE substring(p.idu from 1 for 5) = :insee
            GROUP BY z.zone_lib"""), {"insee": insee, "run": SERVED_RUN}).all()
        if doc is None:
            print(f"{commune:22s}  (non outillée — estimation générique, casse-robuste par uppercase)")
            continue
        keys = set((doc.get("zones") or {}).keys())
        st_liste = set((doc.get("zones_au_st") or {}).get("liste", []) or [])
        n_zones = nomatch = defaut = defaut_parc = defaut_served = 0
        for zl, n, served in zl_rows:
            n_zones += 1
            matched, kind = match_kind(zl, keys, st_liste)
            if matched:
                continue
            nomatch += 1
            k, c = rescue(zl, keys, st_liste)
            if k is not None:   # DÉFAUT normalisable
                defaut += 1; defaut_parc += n; defaut_served += (served or 0)
                detail.append((commune, zl, n, served or 0, k, c))
        tot_def_zones += defaut; tot_def_parc += defaut_parc; tot_def_served += defaut_served
        flag = "  ⚠️" if defaut else ""
        print(f"{commune:22s} {n_zones:5d} {nomatch:7d} {defaut:6d} {defaut_parc:6d} {defaut_served:7d}{flag}")

    print(f"\nTOTAL DÉFAUT normalisable : {tot_def_zones} zones · {tot_def_parc} parcelles · "
          f"{tot_def_served} SERVIES")
    print("\n--- détail des zones en défaut (zl SIG → clé YAML, cause) ---")
    for commune, zl, n, served, k, c in sorted(detail, key=lambda x: -x[3]):
        print(f"  {commune:20s} '{zl}' → '{k}'  [{c}]  {n} parc ({served} servies)")
