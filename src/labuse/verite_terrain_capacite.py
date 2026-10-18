"""VERITE-TERRAIN-2 · volet D — la CAPACITÉ LABUSE face aux vrais permis Sit@del (post-PLU).

Les volets A/B/C ont vérifié ce que LABUSE SERT (règles PLU, trajets, DPE/permis/risques) contre les
sources officielles. Le volet D pose l'autre question, la plus dure : **ce que LABUSE dit CONSTRUCTIBLE
tient-il face à ce qui a été réellement AUTORISÉ ?**

Pour chaque parcelle qui a obtenu un **permis** (PC/DP créant des logements, source Sit@del/SDES ingérée
dans `sitadel_permits`) **depuis l'entrée en vigueur du PLU actuel de sa commune**, on compare :

  · l'AUTORISÉ          = surface habitable créée (`surf_hab`) et logements créés (`nb_lgt`) du permis ;
  · la CAPACITÉ LABUSE  = la SDP max (`surface_plancher_m2`) et les logements estimés que le moteur de
                          faisabilité sert sur la (les) parcelle(s) du permis, dans l'état servi q_v19.

Un permis peut porter sur PLUSIEURS parcelles (réunion foncière, `idu_codes` à N éléments) → on compare
l'autorisé du PROJET à la SOMME des capacités LABUSE sur les parcelles du permis ; si des parcelles ne
sont pas servies (disparues, redécoupées après le permis), on le DIT et on marque le permis partiel.

Deux grilles de comparaison, honnêtes sur leur grain :
  · SDP   : la surface Sit@del est une surface HABITABLE (`surf_hab_creee`), la SDP LABUSE est une
            SURFACE DE PLANCHER (brute). On convertit l'habitable en plancher (× coef plancher, 1,15,
            cf. `score_e.COEF_PLANCHER`) AVANT de faire le ratio — sinon on sous-estime mécaniquement.
  · logements : comparaison DIRECTE, apples-to-apples (nb de logements autorisés vs estimés).

Un permis est AU-DESSUS de la capacité LABUSE si l'autorisé dépasse la capacité LABUSE (ratio > 1 avec
une tolérance). Chaque cas au-dessus est EXPLIQUÉ et CLASSÉ (réunion de parcelles redécoupée, parcelle
non servie/non constructible chez LABUSE, dérogation/densité réelle supérieure au calibrage, surface
Sit@del aberrante, logements sans surface…).

LECTURE SEULE STRICTE : connexion DB `read_only=True` (toute écriture lève), aucun écrit VPS, aucune
modification du code existant. Le moteur de faisabilité est appelé EN LECTURE (il ne mute rien ; il lit
l'état servi q_v19 — zones, PLU calibré, bâti, LiDAR). Pas de réseau ici : tout est local (base +
moteur). CACHE DISQUE par parcelle (capacité LABUSE) et JOURNAL APPEND-ONLY resumable par permis : une
interruption ne perd rien, la reprise saute les permis déjà faits. Séquentiel, foreground.

    PYTHONPATH=src python -m labuse.verite_terrain_capacite run      [--n 0] [--commune 97413]
    PYTHONPATH=src python -m labuse.verite_terrain_capacite rapport
"""
from __future__ import annotations

import csv
import glob
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import psycopg
import yaml

from .verite_terrain import _dsn

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "verite-terrain-2"
CACHE = Path(os.environ.get("VT2D_CACHE", SORTIE / "cache" / "capacite"))
PERMIS_CSV = SORTIE / "PERMIS-VS-CAPACITE.csv"
NOTES_MD = SORTIE / "PERMIS-VS-CAPACITE-NOTES.md"
#: journal APPEND-ONLY — un permis écrit sitôt fini ; reprise en sautant les faits.
PARTIEL_CSV = SORTIE / "_capacite_partiel.csv"
PLU_DIR = RACINE / "config" / "plu_destinations"

#: habitable (Sit@del surf_hab_creee) → plancher (SDP brute LABUSE). Même coef que score_e.COEF_PLANCHER.
COEF_PLANCHER = 1.15
#: au-delà de ce ratio autorisé/LABUSE, le permis est « au-dessus » (10 % de marge = bruit de calibrage).
SEUIL_AU_DESSUS = 1.10
#: surface habitable par logement plausible : au-delà, surf_hab Sit@del est jugée aberrante (donnée source).
SURF_HAB_MAX_PAR_LOGT = 400.0

_COLS = ["permit_id", "commune", "insee", "zones", "date_permis", "millesime_plu", "type",
         "n_parcelles", "n_parcelles_servies", "idu_codes", "sdp_autorisee_shab_m2",
         "sdp_autorisee_plancher_m2", "logements_autorises", "sdp_max_labuse_m2",
         "logements_labuse", "ratio_sdp", "ratio_log", "au_dessus", "cause_si_au_dessus", "note"]


# ═════════════════════════════════════════════════════════════════════════════════════════
#  CONNEXION READ-ONLY + MILLÉSIMES PLU
# ═════════════════════════════════════════════════════════════════════════════════════════

def _connect():
    conn = psycopg.connect(_dsn())
    conn.read_only = True        # garde-fou : toute écriture LÈVE plutôt que de passer
    conn.autocommit = True
    return conn


def _millesimes_plu() -> dict[str, str]:
    """{insee: date d'entrée en vigueur du PLU en cours} depuis config/plu_destinations/<insee>_*.yaml,
    champ `meta.millesime` (ou racine `millesime`). C'est la DATE DU RÈGLEMENT en vigueur — c'est elle
    qui borne « post-PLU » : seuls les permis postérieurs tombent sous les règles que LABUSE modélise."""
    out: dict[str, str] = {}
    for fp in sorted(glob.glob(str(PLU_DIR / "*.yaml"))):
        insee = Path(fp).name.split("_")[0]
        if not insee.isdigit():
            continue
        try:
            d = yaml.safe_load(open(fp)) or {}
        except Exception:  # noqa: BLE001
            continue
        mil = d.get("millesime") or (d.get("meta") or {}).get("millesime")
        if mil:
            out[insee] = str(mil)[:10]
    return out


# ═════════════════════════════════════════════════════════════════════════════════════════
#  CAPACITÉ LABUSE SERVIE (moteur de faisabilité, état q_v19) — mémoïsée + cachée par parcelle
# ═════════════════════════════════════════════════════════════════════════════════════════
#
# Le moteur `parcel_faisabilite` lit l'état SERVI (zones parcel_zone_plu, PLU calibré, bâti BD TOPO/
# CoSIA, hauteur LiDAR) — exactement ce qui alimente la fiche servie q_v19. On en tire :
#   · sdp_max_m2    = fourchette['surface_plancher_m2']  (SDP max brute ; même grandeur que la SDP visée)
#   · logements     = max(logements_au_sol[1], logements_sous_sol[1])  — MÊME formule que bilan.py:404-405
#                     (le haut de fourchette : la capacité, pas le plancher prudent).
# Parcelle non servie / non constructible → sdp_max 0, logements 0 (capacité nulle), avec la cause.

_sess = None


def _session():
    global _sess
    if _sess is None:
        from .db import session_factory
        _sess = session_factory()()
    return _sess


def _cache_cap(idu: str):
    p = CACHE / f"{idu}.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            return None
    return None


def _ecrire_cap(idu: str, payload: dict) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"{idu}.json").write_text(json.dumps(payload, ensure_ascii=False))


def capacite_labuse(conn, idu: str) -> dict:
    """Capacité SERVIE (q_v19) d'UNE parcelle : {existe, servie, constructible, sdp_max_m2,
    logements, zone, cause}. Caché sur disque (clé = idu) — recalcul idempotent, reprise gratuite."""
    hit = _cache_cap(idu)
    if hit is not None:
        return hit
    out = {"idu": idu, "existe": False, "servie": False, "constructible": None,
           "sdp_max_m2": 0.0, "logements": 0, "zone": None, "zone_fam": None, "cause": None}
    with conn.cursor() as cur:
        cur.execute("SELECT id, cadastre_disparue_le FROM parcels WHERE idu=%s", (idu,))
        row = cur.fetchone()
        if not row:
            out["cause"] = "parcelle absente du cadastre servi (disparue/redécoupée)"
            _ecrire_cap(idu, out)
            return out
        pid, disparue = row
        out["existe"] = True
        out["servie"] = disparue is None
        cur.execute("SELECT zone_lib, zone_fam FROM parcel_zone_plu WHERE idu=%s", (idu,))
        z = cur.fetchone()
        if z:
            out["zone"], out["zone_fam"] = z[0], z[1]
        cur.execute("SELECT cause FROM parcel_residuel_runs WHERE run_seq=16 AND parcel_id=%s", (pid,))
        rc = cur.fetchone()
        res_cause = rc[0] if rc else None
    # moteur de faisabilité (lecture seule) — l'état servi q_v19
    try:
        from .faisabilite.db import parcel_faisabilite
        res = parcel_faisabilite(_session(), pid)
    except Exception as e:  # noqa: BLE001 — un calcul qui lève ne doit pas tout bloquer
        out["constructible"] = None
        out["cause"] = f"moteur a levé : {str(e)[:70]}"
        _ecrire_cap(idu, out)
        return out
    if res is None:
        out["constructible"] = False
        out["cause"] = res_cause or "hors PLU outillé — capacité non calculable"
        _ecrire_cap(idu, out)
        return out
    ctx, f = res
    out["constructible"] = bool(f.constructible)
    if out["zone"] is None:
        out["zone"] = getattr(ctx, "zone", None)
    if not f.constructible:
        out["cause"] = res_cause or "non constructible (moteur)"
        _ecrire_cap(idu, out)
        return out
    fr = f.fourchette or {}
    out["sdp_max_m2"] = float(fr.get("surface_plancher_m2") or 0.0)
    las = fr.get("logements_au_sol") or (0, 0)
    lss = fr.get("logements_sous_sol") or (0, 0)
    out["logements"] = int(max(las[1] if len(las) > 1 else 0, lss[1] if len(lss) > 1 else 0))
    _ecrire_cap(idu, out)
    return out


# ═════════════════════════════════════════════════════════════════════════════════════════
#  AUTORISÉ (permis Sit@del) — surface habitable créée, logements créés
# ═════════════════════════════════════════════════════════════════════════════════════════

def _permis_post_plu(conn, millesimes: dict[str, str], insee_filtre: str | None):
    """Permis PC/DP famille 'logements', NON ANNULÉS (etat≠4), créant surface OU logements, portant au
    moins un idu, et dont la date (réelle d'autorisation = colonne `date`, repli `date_depot`) est
    POSTÉRIEURE au millésime PLU de la commune. Trié par permit_id pour une reprise déterministe."""
    inseles = [insee_filtre] if insee_filtre else sorted(millesimes)
    out = []
    for insee in inseles:
        mil = millesimes.get(insee)
        if not mil:
            continue
        with conn.cursor() as cur:
            cur.execute(
                """SELECT permit_id, type,
                          COALESCE(date::date, date_depot) AS d,
                          idu_codes, commune,
                          raw->>'surf_hab' AS surf, raw->>'nb_lgt' AS lgt, raw->>'etat' AS etat
                   FROM sitadel_permits
                   WHERE type IN ('PC','DP') AND raw->>'famille'='logements'
                     AND raw->>'insee'=%s
                     AND COALESCE(date::date, date_depot) > %s::date
                     AND COALESCE(raw->>'etat','') <> '4'
                     AND idu_codes IS NOT NULL AND jsonb_array_length(idu_codes) >= 1
                     AND ( ((raw->>'surf_hab') ~ '^[0-9]' AND (raw->>'surf_hab')::float > 0)
                        OR ((raw->>'nb_lgt') ~ '^[0-9]+$' AND (raw->>'nb_lgt')::int > 0) )
                   ORDER BY permit_id""",
                (insee, mil))
            for pid, typ, d, codes, commune, surf, lgt, etat in cur.fetchall():
                out.append({"permit_id": pid, "type": typ, "date": d.isoformat() if d else "",
                            "insee": insee, "commune": commune, "millesime": mil,
                            "idu_codes": list(codes), "surf_hab": _num(surf), "nb_lgt": _int(lgt),
                            "etat": etat})
    out.sort(key=lambda p: (p["permit_id"] or ""))
    return out


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


# ═════════════════════════════════════════════════════════════════════════════════════════
#  COMPARAISON PERMIS ↔ CAPACITÉ (somme des parcelles, grain réunion foncière)
# ═════════════════════════════════════════════════════════════════════════════════════════

def comparer_permis(conn, p: dict) -> dict:
    caps = [capacite_labuse(conn, idu) for idu in p["idu_codes"]]
    n_parc = len(caps)
    servies = [c for c in caps if c["servie"]]
    n_servies = len(servies)
    sdp_labuse = sum(c["sdp_max_m2"] for c in servies)
    log_labuse = sum(c["logements"] for c in servies)
    zones = sorted({(c["zone"] or "?") for c in caps})
    zone_fams = sorted({(c["zone_fam"] or "?") for c in caps if c["zone_fam"]})

    surf_shab = p["surf_hab"]
    sdp_aut = surf_shab * COEF_PLANCHER        # habitable → plancher (pour comparer à la SDP brute LABUSE)
    log_aut = p["nb_lgt"]

    ratio_sdp = (sdp_aut / sdp_labuse) if sdp_labuse > 0 else (float("inf") if sdp_aut > 0 else None)
    ratio_log = (log_aut / log_labuse) if log_labuse > 0 else (float("inf") if log_aut > 0 else None)

    # « au-dessus » = l'autorisé dépasse la capacité LABUSE sur AU MOINS une des deux grandeurs
    # mesurables (SDP OU logements), au-delà de la tolérance. On privilégie la grandeur disponible.
    au_sdp = (ratio_sdp is not None and ratio_sdp > SEUIL_AU_DESSUS)
    au_log = (ratio_log is not None and ratio_log > SEUIL_AU_DESSUS)
    au_dessus = bool(au_sdp or au_log)

    cause, note = _classer(p, caps, servies, n_parc, n_servies, sdp_aut, log_aut,
                           sdp_labuse, log_labuse, au_dessus, au_sdp, au_log)

    return {
        "permit_id": p["permit_id"], "commune": p["commune"], "insee": p["insee"],
        "zones": "|".join(zones) + (f" ({'|'.join(zone_fams)})" if zone_fams else ""),
        "date_permis": p["date"], "millesime_plu": p["millesime"], "type": p["type"],
        "n_parcelles": n_parc, "n_parcelles_servies": n_servies,
        "idu_codes": " ".join(p["idu_codes"]),
        "sdp_autorisee_shab_m2": round(surf_shab),
        "sdp_autorisee_plancher_m2": round(sdp_aut),
        "logements_autorises": log_aut,
        "sdp_max_labuse_m2": round(sdp_labuse),
        "logements_labuse": log_labuse,
        "ratio_sdp": _r(ratio_sdp), "ratio_log": _r(ratio_log),
        "au_dessus": au_dessus, "cause_si_au_dessus": cause if au_dessus else "",
        "note": note,
    }


def _r(x):
    if x is None:
        return ""
    if x == float("inf"):
        return "inf"
    return round(x, 3)


def _classer(p, caps, servies, n_parc, n_servies, sdp_aut, log_aut, sdp_labuse, log_labuse,
             au_dessus, au_sdp, au_log) -> tuple[str, str]:
    """Classe la CAUSE d'un permis au-dessus de la capacité LABUSE (ou la note descriptive sinon).
    Ordre de priorité des causes = de la plus structurelle (grain/foncier) à la plus métier (calibrage)."""
    non_servies = [c for c in caps if not c["existe"]]
    non_constr = [c for c in servies if c["constructible"] is False]
    surf_par_logt = (p["surf_hab"] / p["nb_lgt"]) if p["nb_lgt"] > 0 else None

    # --- notes descriptives communes (servent aussi aux conformes) ---
    bits = []
    if n_parc > 1:
        bits.append(f"réunion de {n_parc} parcelle(s)")
    if non_servies:
        bits.append(f"{len(non_servies)}/{n_parc} parcelle(s) non servie(s) (disparue/redécoupée)")
    if non_constr:
        bits.append(f"{len(non_constr)} parcelle(s) non constructible(s) chez LABUSE "
                    f"({', '.join(sorted({c['cause'] or '?' for c in non_constr}))[:70]})")
    note = " ; ".join(bits)

    if not au_dessus:
        return "", note or "LABUSE couvre l'autorisé (capacité ≥ permis)"

    # --- cause (permis au-dessus), par ordre de priorité ---
    # 1) surface Sit@del aberrante (donnée source) : >400 m² habitables / logement.
    if au_sdp and surf_par_logt is not None and surf_par_logt > SURF_HAB_MAX_PAR_LOGT:
        return ("surface Sit@del aberrante",
                (note + " ; " if note else "")
                + f"surf_hab {p['surf_hab']:.0f} m² / {p['nb_lgt']} logt = "
                  f"{surf_par_logt:.0f} m²/logt (invraisemblable, erreur de la source Sit@del)")
    # 2) aucune parcelle du permis n'existe plus chez LABUSE → rien à comparer honnêtement.
    if n_servies == 0:
        return ("parcelle non servie",
                (note + " ; " if note else "")
                + "aucune parcelle du permis n'est servie par LABUSE (foncier redécoupé après le permis)")
    # 3) capacité LABUSE NULLE alors que le permis a construit → parcelle non constructible chez LABUSE.
    if sdp_labuse == 0 and log_labuse == 0:
        if non_constr:
            return ("non constructible LABUSE",
                    (note + " ; " if note else "")
                    + "LABUSE classe la (les) parcelle(s) non constructible(s) alors qu'un permis "
                      "logements y a été autorisé")
        return ("capacite nulle LABUSE",
                (note + " ; " if note else "") + "capacité LABUSE nulle sur parcelle(s) servie(s)")
    # 4) réunion foncière : plusieurs parcelles, ou des parcelles non servies → somme incomplète.
    if n_parc > 1 and (n_servies < n_parc or non_servies):
        return ("réunion de parcelles incomplète",
                (note + " ; " if note else "")
                + "projet sur plusieurs parcelles dont certaines ne sont pas servies → somme des "
                  "capacités LABUSE sous-estimée")
    # 5) densité réelle > calibrage : parcelle(s) servie(s), capacité LABUSE positive mais dépassée.
    #    (dérogation, densité réelle supérieure au gabarit modélisé, PLU calibré prudent…)
    detail = []
    if au_sdp:
        detail.append(f"SDP autorisée {sdp_aut:.0f} m² (plancher, = {p['surf_hab']:.0f} m² hab.×{COEF_PLANCHER}) "
                      f"> SDP max LABUSE {sdp_labuse:.0f} m²")
    if au_log:
        detail.append(f"{log_aut} logements autorisés > {log_labuse} estimés LABUSE")
    return ("densité réelle > calibrage LABUSE",
            (note + " ; " if note else "") + " ; ".join(detail))


# ═════════════════════════════════════════════════════════════════════════════════════════
#  JOURNAL APPEND-ONLY + REPRISE (par permit_id)
# ═════════════════════════════════════════════════════════════════════════════════════════

def _faits() -> set[str]:
    if not PARTIEL_CSV.exists():
        return set()
    with open(PARTIEL_CSV, newline="") as f:
        return {r["permit_id"] for r in csv.DictReader(f) if r.get("permit_id")}


def _ouvrir_journal():
    SORTIE.mkdir(parents=True, exist_ok=True)
    nouveau = not PARTIEL_CSV.exists()
    jour = open(PARTIEL_CSV, "a", newline="")
    w = csv.DictWriter(jour, fieldnames=_COLS)
    if nouveau:
        w.writeheader()
        jour.flush()
    return jour, w


# ═════════════════════════════════════════════════════════════════════════════════════════
#  ORCHESTRATION (séquentielle, foreground, resumable)
# ═════════════════════════════════════════════════════════════════════════════════════════

def _run(n: int, insee_filtre: str | None) -> None:
    conn = _connect()
    millesimes = _millesimes_plu()
    permis = _permis_post_plu(conn, millesimes, insee_filtre)
    if n:
        permis = permis[:n]
    deja = _faits()
    a_faire = [p for p in permis if p["permit_id"] not in deja]
    print(f"{len(permis)} permis post-PLU retenus · {len(deja)} déjà faits · {len(a_faire)} à faire "
          f"(communes : {len({p['insee'] for p in permis})})", flush=True)
    jour, w = _ouvrir_journal()
    try:
        for i, p in enumerate(a_faire, 1):
            try:
                ligne = comparer_permis(conn, p)
            except Exception as e:  # noqa: BLE001 — un permis qui lève ne perd pas les autres
                ligne = {c: "" for c in _COLS}
                ligne.update({"permit_id": p["permit_id"], "commune": p["commune"],
                              "insee": p["insee"], "idu_codes": " ".join(p["idu_codes"]),
                              "note": f"comparaison a levé : {str(e)[:70]}"})
            w.writerow(ligne)
            jour.flush()                 # flush → un permis fini survit à un kill
            if i % 200 == 0:
                print(f"  {i}/{len(a_faire)} permis comparés…", flush=True)
    finally:
        jour.close()
        conn.close()
    _finaliser()


def _finaliser() -> None:
    if not PARTIEL_CSV.exists():
        print("rien à finaliser (journal absent)")
        return
    with open(PARTIEL_CSV, newline="") as f:
        lignes = list(csv.DictReader(f))
    # dédoublonnage (dernière occurrence d'un permit_id gagne) + tri déterministe
    par_id = {l["permit_id"]: l for l in lignes}
    lignes = sorted(par_id.values(), key=lambda l: (l["insee"], l["permit_id"]))
    with open(PERMIS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_COLS)
        w.writeheader()
        w.writerows(lignes)
    print(f"\n{len(lignes)} permis → {PERMIS_CSV}")
    _ecrire_notes(lignes)


# ═════════════════════════════════════════════════════════════════════════════════════════
#  RAPPORT (NOTES.md) — écart médian, dispersion, par commune & par zone, détail des au-dessus
# ═════════════════════════════════════════════════════════════════════════════════════════

def _f(x):
    try:
        v = float(x)
        return v
    except (TypeError, ValueError):
        return None


def _stats(vals: list[float]) -> dict:
    vals = [v for v in vals if v is not None and v != float("inf")]
    if not vals:
        return {"n": 0, "med": None, "q1": None, "q3": None, "iqr": None, "min": None, "max": None}
    vals.sort()
    med = statistics.median(vals)
    if len(vals) >= 4:
        q = statistics.quantiles(vals, n=4)
        q1, q3 = q[0], q[2]
    else:
        q1 = q3 = med
    return {"n": len(vals), "med": med, "q1": q1, "q3": q3, "iqr": q3 - q1,
            "min": vals[0], "max": vals[-1]}


def _fmt(x, d=2):
    return "—" if x is None else f"{x:.{d}f}"


def _ecrire_notes(lignes: list[dict]) -> None:
    n = len(lignes)
    communes = sorted({l["commune"] for l in lignes})
    au_dessus = [l for l in lignes if str(l["au_dessus"]).lower() in ("true", "1")]
    couverts = [l for l in lignes if l not in au_dessus]
    # ratios mesurables
    rsdp = [_f(l["ratio_sdp"]) for l in lignes if _f(l["ratio_sdp"]) is not None]
    rlog = [_f(l["ratio_log"]) for l in lignes if _f(l["ratio_log"]) is not None]
    rsdp_inf = sum(1 for l in lignes if l["ratio_sdp"] == "inf")
    rlog_inf = sum(1 for l in lignes if l["ratio_log"] == "inf")
    s_sdp, s_log = _stats(rsdp), _stats(rlog)
    causes = Counter(l["cause_si_au_dessus"] for l in au_dessus if l["cause_si_au_dessus"])

    # par commune
    par_commune: dict[str, list[dict]] = defaultdict(list)
    for l in lignes:
        par_commune[l["commune"]].append(l)
    # par famille de zone : on préfère la FAMILLE servie (zone_fam, entre parenthèses du champ 'zones'),
    # repli sur le libellé de zone normalisé (en retirant un préfixe numérique de phase AU : 1AUc→AU).
    def _famille(l):
        champ = l["zones"] or ""
        if "(" in champ:                       # 'Ua (U)' / '1AUc (AU)' → la famille entre parenthèses
            fam = champ.split("(", 1)[1].rstrip(")").split("|")[0].strip()
            if fam and fam != "?":
                return fam
        z = champ.split(" (")[0].split("|")[0].lstrip("0123456789").upper()
        for pfx in ("AU", "U", "A", "N"):
            if z.startswith(pfx):
                return pfx
        return z or "?"
    par_zone: dict[str, list[dict]] = defaultdict(list)
    for l in lignes:
        par_zone[_famille(l)].append(l)

    def _bloc(grp: dict[str, list[dict]], titre: str) -> list[str]:
        out = [f"| {titre} | permis | ≤ capacité | au-dessus | méd. ratio SDP | IQR SDP | "
               f"méd. ratio logts | IQR logts |",
               "|---|---|---|---|---|---|---|---|"]
        for k in sorted(grp, key=lambda k: -len(grp[k])):
            g = grp[k]
            ad = [x for x in g if str(x["au_dessus"]).lower() in ("true", "1")]
            ssdp = _stats([_f(x["ratio_sdp"]) for x in g])
            slog = _stats([_f(x["ratio_log"]) for x in g])
            out.append(f"| {k} | {len(g)} | {len(g)-len(ad)} | {len(ad)} | "
                       f"{_fmt(ssdp['med'])} | {_fmt(ssdp['iqr'])} | "
                       f"{_fmt(slog['med'])} | {_fmt(slog['iqr'])} |")
        return out

    md = []
    md += [
        "# VERITE-TERRAIN-2 — volet D : la capacité LABUSE face aux vrais permis Sit@del (post-PLU)",
        "",
        "Les volets A/B/C ont vérifié ce que LABUSE **sert** (règles PLU, trajets, DPE/permis/risques) "
        "contre les sources. Le volet D pose l'autre question : **ce que LABUSE dit constructible "
        "tient-il face à ce qui a été réellement autorisé ?** Pour chaque parcelle ayant obtenu un "
        "permis logements (Sit@del/SDES) **depuis l'entrée en vigueur du PLU en cours de sa commune**, "
        "on compare l'**autorisé** (surface habitable créée, logements créés) à la **capacité LABUSE** "
        "servie en q_v19 (SDP max du moteur de faisabilité, logements estimés).",
        "",
        "Lecture seule stricte (DB `read_only=True`, aucun écrit, aucune modif de code existant). Le "
        "moteur de faisabilité est appelé **en lecture** sur l'état servi q_v19. Un seul module neuf : "
        "`src/labuse/verite_terrain_capacite.py`. Cache disque par parcelle "
        "(`cache/capacite/`, non commité) + journal append-only resumable "
        "(`_capacite_partiel.csv`, non commité). Livrable : `PERMIS-VS-CAPACITE.csv` "
        f"({n} lignes = 1 par permis) + ce NOTES.",
        "",
        "---",
        "",
        "## 0. Verdict d'ensemble",
        "",
        f"- **{n} permis** post-PLU retenus sur **{len(communes)} communes**.",
        f"- **Filtre** : PC/DP, famille « logements », **non annulés** (ETAT_DAU ≠ 4), créant une "
        f"surface habitable OU des logements (`surf_hab_creee` > 0 ou `nb_lgt_tot_crees` > 0), portant "
        f"au moins un IDU, **date d'autorisation postérieure au millésime du PLU** de la commune.",
        f"- **{len(couverts)} permis ({len(couverts)/n*100:.1f} %) ≤ capacité LABUSE** (LABUSE couvre "
        f"l'autorisé) · **{len(au_dessus)} ({len(au_dessus)/n*100:.1f} %) au-dessus** (LABUSE "
        f"sous-estime ou ne sert pas).",
        "",
        "### Écart médian & dispersion (ratio autorisé / LABUSE)",
        "",
        "| grandeur | n mesurable | médiane | Q1 | Q3 | IQR | min | max | ratios « inf » (LABUSE=0) |",
        "|---|---|---|---|---|---|---|---|---|",
        f"| **SDP** (plancher) | {s_sdp['n']} | {_fmt(s_sdp['med'])} | {_fmt(s_sdp['q1'])} | "
        f"{_fmt(s_sdp['q3'])} | {_fmt(s_sdp['iqr'])} | {_fmt(s_sdp['min'])} | {_fmt(s_sdp['max'])} | "
        f"{rsdp_inf} |",
        f"| **logements** | {s_log['n']} | {_fmt(s_log['med'])} | {_fmt(s_log['q1'])} | "
        f"{_fmt(s_log['q3'])} | {_fmt(s_log['iqr'])} | {_fmt(s_log['min'])} | {_fmt(s_log['max'])} | "
        f"{rlog_inf} |",
        "",
        "Ratio = autorisé / capacité LABUSE. **< 1 = LABUSE couvre** (capacité ≥ autorisé) ; **> 1 = "
        "LABUSE sous-estime** (autorisé plus grand). « inf » = capacité LABUSE nulle alors que le "
        "permis a créé quelque chose (classé en cause ci-dessous). La médiane est donnée **telle "
        "quelle**, sans retrait d'aberrants.",
        "",
        "### Cause dominante des permis au-dessus",
        "",
        "| cause | permis |",
        "|---|---|",
    ]
    for c, k in causes.most_common():
        md.append(f"| {c} | {k} |")
    md += [
        "",
        "---",
        "",
        "## 1. Méthode",
        "",
        "### 1.1 Autorisé = Sit@del/SDES (`sitadel_permits`)",
        "",
        "- **Source** : table `sitadel_permits` (permis ingérés de Sit@del3/SDES). Famille "
        "« logements », type PC ou DP. **Annulés exclus** (`raw->>'etat' = '4'` = ETAT_DAU annulé, "
        "cf. `ingestion/permits.ETAT_LABELS`) — on garde autorisés / travaux commencés / achevés.",
        "- **Surface créée** : `raw->>'surf_hab'` = `surf_hab_creee` = **surface HABITABLE** créée "
        "(libellé source « m² hab. », `ingestion/permits._nature`). Ce n'est **pas** une surface de "
        "plancher. On la convertit en plancher (**× 1,15**, coef `score_e.COEF_PLANCHER`) avant de la "
        "comparer à la SDP brute LABUSE, sinon le ratio sous-estime mécaniquement.",
        "- **Logements créés** : `raw->>'nb_lgt'` = `nb_lgt_tot_crees`. Comparaison directe.",
        "- **Date** : colonne `date` = `date_reelle_autorisation` (date réelle d'autorisation, "
        "`ingestion/permits.ingest_permits`) ; repli `date_depot` si `date` nulle. **C'est la date "
        "d'autorisation** qui borne « post-PLU ».",
        "- **Réunion foncière** : `idu_codes` (jsonb) = liste des parcelles du permis ; "
        f"les projets multi-parcelles ({sum(1 for l in lignes if int(l['n_parcelles'] or 1) > 1)} "
        "permis ici) sont comparés à la **somme** des capacités LABUSE de leurs parcelles servies.",
        "",
        "### 1.2 Entrée en vigueur du PLU",
        "",
        "`config/plu_destinations/<insee>_*.yaml`, champ `meta.millesime` = **date du règlement en "
        "vigueur** (relu au PDF/GPU dans les volets A et CALIBRAGE). Seuls les permis **postérieurs** "
        "à cette date sont retenus : avant, les règles que LABUSE modélise ne s'appliquaient pas. Les "
        "millésimes vont de 2007 (Saint-Leu, le plus ancien → quasi tous ses permis sont « post-PLU ») "
        "à 2026 (Saint-Denis, Bras-Panon → très peu de permis postérieurs).",
        "",
        "### 1.3 Capacité LABUSE servie (q_v19)",
        "",
        "Run servi confirmé par `config/served_manifest.json` : `scoring_run = q_v19`, "
        "`residuel_run_seq = 16`, `residuel_runs` ligne `run_seq 16` / label `q_v19` / `is_served = t`. "
        "La capacité est lue par le **moteur de faisabilité** (`faisabilite.db.parcel_faisabilite`) "
        "**en lecture** sur l'état servi (zones `parcel_zone_plu`, PLU calibré, bâti BD TOPO/CoSIA, "
        "hauteur LiDAR) — exactement ce qui alimente la fiche servie q_v19. On en tire, par parcelle :",
        "",
        "- **SDP max** = `fourchette['surface_plancher_m2']` (surface de plancher max, grandeur brute).",
        "- **logements estimés** = `max(logements_au_sol[1], logements_sous_sol[1])` — **exactement la "
        "formule servie** (`faisabilite/bilan.py:404-405`), le haut de fourchette (la capacité).",
        "- parcelle non servie / non constructible → SDP max 0, logements 0, avec la cause servie "
        "(`parcel_residuel_runs.cause`, run 16).",
        "",
        "**Grain** : la comparaison est au grain **permis** (projet), pas parcelle isolée — l'autorisé "
        "d'un projet est confronté à la **somme** des capacités LABUSE des parcelles du permis.",
        "",
        "---",
        "",
        "## 2. Écart médian & dispersion par commune",
        "",
    ]
    md += _bloc(par_commune, "commune")
    md += [
        "",
        "## 3. Écart médian & dispersion par famille de zone PLU",
        "",
        "Famille = `parcel_zone_plu.zone_fam` servie, repli sur la zone normalisée (préfixe de phase AU "
        "retiré : 1AUc→AU) : U (urbain), AU (à urbaniser), A (agricole), N (naturel). `?` = permis dont "
        "aucune parcelle n'est servie (foncier redécoupé) → sans zone ni ratio mesurable.",
        "",
    ]
    md += _bloc(par_zone, "zone")

    # --- détail des au-dessus, un par un, groupés par cause ---
    md += ["", "---", "", "## 4. Les permis au-dessus de la capacité LABUSE, un par un", "",
           f"**{len(au_dessus)} permis** dépassent la capacité LABUSE (ratio SDP ou logements > "
           f"{SEUIL_AU_DESSUS:.2f}). Classés par cause, du plus structurel au plus métier.", ""]
    par_cause: dict[str, list[dict]] = defaultdict(list)
    for l in au_dessus:
        par_cause[l["cause_si_au_dessus"] or "(sans cause)"].append(l)
    for cause in sorted(par_cause, key=lambda c: -len(par_cause[c])):
        grp = par_cause[cause]
        md += [f"### {cause} — {len(grp)} permis", "",
               "| permit_id | commune | zone(s) | date | n parc. (servies) | SDP aut. (planch.) m² | "
               "logts aut. | SDP max LABUSE m² | logts LABUSE | ratio SDP | ratio logts | note |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        # limiter l'affichage détaillé si une cause est volumineuse (table reste lisible)
        affiches = grp if len(grp) <= 60 else grp[:60]
        for l in sorted(affiches, key=lambda x: (x["commune"], x["permit_id"])):
            md.append(
                f"| {l['permit_id']} | {l['commune']} | {l['zones']} | {l['date_permis']} | "
                f"{l['n_parcelles']} ({l['n_parcelles_servies']}) | {l['sdp_autorisee_plancher_m2']} | "
                f"{l['logements_autorises']} | {l['sdp_max_labuse_m2']} | {l['logements_labuse']} | "
                f"{l['ratio_sdp']} | {l['ratio_log']} | {l['note'][:120]} |")
        if len(grp) > 60:
            md.append(f"| … | … | … | … | … | … | … | … | … | … | … | "
                      f"(+{len(grp)-60} autres de même cause, voir CSV) |")
        md.append("")

    md += [
        "---",
        "",
        "## 5. Limites honnêtes",
        "",
        "1. **Grain SDP ≠ grain permis.** Sit@del publie une surface **habitable** (`surf_hab_creee`), "
        "LABUSE une **surface de plancher** (brute). On convertit habitable → plancher (× 1,15) mais le "
        "coef est une moyenne : un projet avec beaucoup de circulations/parkings aura un vrai coef "
        "supérieur, donc le ratio SDP est **légèrement conservateur** (tend à sous-dire les dépassements).",
        "2. **Réunion de parcelles redécoupée.** Quand un permis a été autorisé puis le foncier "
        "redécoupé, `idu_codes` peut pointer des parcelles **disparues** : la somme des capacités "
        "LABUSE est alors incomplète et le ratio gonfle artificiellement. Ces cas sont **marqués** "
        f"(`n_parcelles_servies < n_parcelles`) et classés « réunion de parcelles incomplète » ou "
        "« parcelle non servie », jamais comptés comme une erreur de calibrage.",
        "3. **Surfaces non-logement / mixtes.** Un PC « logements » peut inclure du commerce/tertiaire "
        "au RDC : `surf_hab_creee` ne compte que l'habitable, mais `nb_lgt` reste le nombre de "
        "logements — la comparaison logements est la plus fiable pour ces projets.",
        "4. **Surfaces source aberrantes.** Quelques permis Sit@del portent une `surf_hab` "
        "invraisemblable (> 400 m² habitables / logement) : erreur de saisie de la source, **isolée** "
        "en cause « surface Sit@del aberrante » et non imputée à LABUSE.",
        "5. **Permis pré-PLU résiduels.** On borne par la **date réelle d'autorisation** ; si cette "
        "date est nulle on retombe sur `date_depot`. Un permis déposé juste après le PLU mais instruit "
        "sous l'ancien règlement peut subsister — effet de bord assumé, minoritaire.",
        "6. **N réel.** Saint-Leu (PLU 2007), Saint-André (2019) et Saint-Benoît (2020) pèsent la "
        "majorité des permis (millésimes anciens → longue fenêtre) ; les communes à PLU 2025-2026 "
        "n'ont que quelques permis postérieurs. Les médianes par commune de ces dernières reposent "
        "sur de petits effectifs (lire la colonne « permis »).",
        "7. **Capacité = SDP MAX, pas résiduelle.** On compare l'autorisé à la SDP **max** du gabarit "
        "(ce que la parcelle peut porter au total), pas à la SDP **résiduelle** (max − existant). Un "
        "permis sur terrain déjà partiellement bâti peut donc être « couvert » par la SDP max sans que "
        "le résiduel servi (plus petit) ne l'eût prédit — choix assumé : on teste le **gabarit**, pas "
        "le reste à bâtir.",
        "",
    ]
    NOTES_MD.write_text("\n".join(md) + "\n")
    print(f"→ {NOTES_MD}")


def main(argv: list[str] | None = None) -> None:
    import argparse
    pa = argparse.ArgumentParser(prog="labuse.verite_terrain_capacite")
    sub = pa.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--n", type=int, default=0, help="0 = tous les permis post-PLU")
    pr.add_argument("--commune", default=None, help="INSEE à filtrer (ex. 97413)")
    sub.add_parser("rapport")
    a = pa.parse_args(argv)
    if str(RACINE) not in sys.path:
        sys.path.insert(0, str(RACINE))
    if a.cmd == "run":
        _run(a.n, a.commune)
    elif a.cmd == "rapport":
        _finaliser()


if __name__ == "__main__":
    main()
