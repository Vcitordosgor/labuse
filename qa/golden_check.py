#!/usr/bin/env python
"""golden_check.py — contrôleur du golden dataset M6 Phase 1 §1.2 (LECTURE SEULE).

Compare l'état courant (base PostgreSQL + API) à la référence versionnée
reports/m6-audit/golden/golden-parcelles.json, champ par champ, avec tolérances.

Usage (à lancer après chaque refresh de données) :
    python qa/golden_check.py                     # contrôle complet, PASS/FAIL par parcelle/champ
    python qa/golden_check.py --idu 97410000AS1425 [...]   # limite aux parcelles données
    python qa/golden_check.py --dump              # imprime l'état courant collecté (JSON) sur stdout
                                                  # (sert à régénérer la référence : ... --dump > golden-parcelles.json)
    python qa/golden_check.py --golden CHEMIN     # autre fichier de référence

Environnement :
    LABUSE_DATABASE_URL  (défaut postgresql://openclaw@localhost:5432/labuse — la partie +psycopg est acceptée)
    LABUSE_QA_TARGET     cible QA distante (M7 : le VPS) — prime sur LABUSE_API_BASE
    LABUSE_API_BASE      (défaut http://127.0.0.1:8010)
    (--base-url prime sur les deux ; la face DB suit LABUSE_DATABASE_URL)

Code retour : 0 si 100 % PASS, 1 si au moins un écart (FAIL), 2 si erreur d'exécution.

Garanties : le script ne fait QUE des SELECT en base et des GET sur l'API ; il n'écrit
aucun fichier (le --dump écrit sur stdout, à rediriger soi-même).

Notes de conception :
  * La référence fige les valeurs des DEUX faces (db / api) + les contrôles de cohérence
    base↔API (`coherence`). Après un refresh, un écart signale soit une régression, soit
    une évolution légitime des données : dans ce second cas, régénérer la référence
    (--dump) et versionner le diff.
  * Le run v2 comparé est le run SERVI (dernier de p_score_v2_runs, même règle que l'API).
    Si le run_id a changé depuis la référence, chaque parcelle l'affiche en WARN :
    les écarts tier/rang sont alors attendus.
  * Tolérances (suffixe de champ → tolérance absolue) : voir TOLERANCES ci-dessous.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

DB_URL = (os.environ.get("LABUSE_DATABASE_URL")
          or "postgresql://openclaw@localhost:5432/labuse").replace("+psycopg", "")
# Pré-vol M7 P2 — cible QA paramétrable : --base-url > LABUSE_QA_TARGET > LABUSE_API_BASE > localhost.
# Défaut inchangé (localhost:8010). C'est le geste que M7 fera contre le VPS.
API_BASE = os.environ.get("LABUSE_QA_TARGET",
                          os.environ.get("LABUSE_API_BASE", "http://127.0.0.1:8010")).rstrip("/")
# M8b — run cascade lu par le golden. Défaut = run SERVI (source unique Q_A_RUN_LABEL), plus
# « q_v3_datagap » codé en dur (run mort). Override `LABUSE_GOLDEN_RUN_LABEL` pour tester un candidat.
RUN_LABEL = os.environ.get("LABUSE_GOLDEN_RUN_LABEL")
if not RUN_LABEL:
    try:
        from labuse.scoring.score_v_constants import Q_A_RUN_LABEL as RUN_LABEL
    except Exception:
        RUN_LABEL = "q_v5_m6b"
DEFAULT_GOLDEN = os.path.join(os.path.dirname(__file__), "..",
                              "reports", "m6-audit", "golden", "golden-parcelles.json")

#: liste canonique du golden set (fallback pour --dump quand la référence n'existe pas encore)
GOLDEN_IDUS = [
    # témoins M5.1
    "97410000AS1425", "97410000CD0905", "97423000AB1908", "97423000AB1341", "97415000EY1509",
    # brûlantes
    "97411000KA0296", "97422000AD1237", "97403000AR1423", "97418000AT2379", "97413000CD0729",
    # chaudes
    "97408000AP1647", "97415000CX1395", "97410000AS1450", "97422000AX1253",
    "97420000AO0654", "97407000BI0350",
    # réserve foncière
    "97408000AC1870", "97416000CR1351", "97409000AX0289",
    # à creuser
    "97415000CW1056", "97413000CS0160", "97411000AL0360", "97402000AK1725", "97424000AI0355",
    # écartées v2 riches en couches
    "97413000DM0210", "97422000BY0489",
    # étage 0, un motif chacun
    "97424000AD0409", "97416000CD0765", "97411000AO0748", "97419000AC0159",
    "97421000AC0156", "97405000AB0168",
]

#: tolérances ABSOLUES par suffixe de chemin de champ (sinon : égalité stricte)
TOLERANCES: dict[str, float] = {
    "mult_base": 0.011,
    "percentile": 0.11,
    "surface_m2": 1.0,
    "canopee_pct": 2.0,
    "ndvi_moyen": 0.03,
    "prod_spec_kwh_kwc": 5.0,
    "distance_cote_m": 10.0,
    "pente_moy_deg": 0.5,
    "obstruction_pct": 2.0,
}


def _jsonable(v: Any) -> Any:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, float):
        return round(v, 4) if math.isfinite(v) else None
    return v


def _row(cur, sql: str, **params) -> dict | None:
    cur.execute(sql, params)
    r = cur.fetchone()
    return {k: _jsonable(v) for k, v in r.items()} if r else None


def _all(cur, sql: str, **params) -> list[dict]:
    cur.execute(sql, params)
    return [{k: _jsonable(v) for k, v in r.items()} for r in cur.fetchall()]


def served_v2_run(cur) -> str | None:
    r = _row(cur, "SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")
    return r["run_id"] if r else None


_ZONE_RE = re.compile(r"Zone(?: PLU)? «?\s*([A-Za-z0-9\-_/]+)\s*»?", re.UNICODE)
_PCT_RE = re.compile(r"recouvrement\s+(\d+)\s*%")


def collect_db(cur, idu: str, v2run: str | None) -> dict:
    """Fiche de référence côté base — un SELECT par couche, aucune écriture."""
    head = _row(cur, """
        SELECT p.id AS parcel_id, p.commune, p.section, p.numero,
               round(p.surface_m2)::int AS surface_m2,
               d.matrice_statut, d.status AS cascade_status,
               d.q_score, d.a_score, d.a_completude, d.completeness_score,
               (d.status IN ('exclue','faux_positif_probable')) AS etage0
        FROM parcels p
        LEFT JOIN dryrun_parcel_evaluations d
               ON d.parcel_id = p.id AND d.run_label = %(run)s
        WHERE p.idu = %(idu)s""", idu=idu, run=RUN_LABEL)
    if not head:
        return {"absente": True}
    pid = head.pop("parcel_id")

    motifs = [r["layer_name"] for r in _all(cur, """
        SELECT DISTINCT layer_name FROM dryrun_cascade_results
        WHERE run_label = %(run)s AND parcel_id = %(pid)s AND result = 'HARD_EXCLUDE'
        ORDER BY layer_name""", run=RUN_LABEL, pid=pid)]

    zon = _row(cur, """
        SELECT detail FROM dryrun_cascade_results
        WHERE run_label = %(run)s AND parcel_id = %(pid)s AND layer_name = 'zonage_plu_gpu'
        ORDER BY id LIMIT 1""", run=RUN_LABEL, pid=pid)
    zonage = None
    if zon:
        mz, mp = _ZONE_RE.search(zon["detail"] or ""), _PCT_RE.search(zon["detail"] or "")
        zonage = {"detail": zon["detail"],
                  "zone": mz.group(1) if mz else None,
                  "recouvrement_pct": int(mp.group(1)) if mp else None}

    risques = [r["detail"] for r in _all(cur, """
        SELECT detail FROM dryrun_cascade_results
        WHERE run_label = %(run)s AND parcel_id = %(pid)s AND layer_name = 'risques'
        ORDER BY detail""", run=RUN_LABEL, pid=pid)]

    v2 = _row(cur, """
        SELECT tier, rang, round(mult_base::numeric, 2)::float AS mult_base,
               round(percentile::numeric, 1)::float AS percentile, copro,
               model_version, event_date
        FROM parcel_p_score_v2
        WHERE run_id = %(r)s AND parcelle_id = %(idu)s""", r=v2run, idu=idu) if v2run else None

    vue_mer = _row(cur, """
        SELECT vue, distance_cote_m, obstruction_pct
        FROM parcel_vue_mer WHERE parcel_id = %(pid)s""", pid=pid)
    solar = _row(cur, """
        SELECT score_solaire, round(prod_spec_kwh_kwc)::int AS prod_spec_kwh_kwc, pv_existant
        FROM parcel_solar WHERE idu = %(idu)s""", idu=idu)
    piscine = _row(cur, """
        SELECT count(*) FILTER (WHERE validation = 'ok')::int AS validees,
               count(*)::int AS detections
        FROM ortho_detections WHERE idu = %(idu)s AND type = 'piscine'""", idu=idu)
    dpe = _row(cur, """
        SELECT count(*)::int AS n, max(etiquette_dpe) AS pire_etiquette,
               max(date_etablissement) AS derniere_date
        FROM dpe_records WHERE parcelle_idu = %(idu)s""", idu=idu)
    if dpe and dpe["n"] == 0:
        dpe = None
    vegetation = _row(cur, """
        SELECT round(canopee_pct)::int AS canopee_pct,
               round(ndvi_moyen::numeric, 2)::float AS ndvi_moyen
        FROM parcel_vegetation WHERE idu = %(idu)s""", idu=idu)
    copro = _row(cur, """
        SELECT count(*)::int AS n, coalesce(sum(nb_lots_total), 0)::int AS lots_total
        FROM rnic_coproprietes WHERE parcelle_idu = %(idu)s""", idu=idu)
    veille = _row(cur, """
        SELECT dirigeant_age, sci_dormante
        FROM parcel_veille_succession WHERE parcelle_id = %(idu)s""", idu=idu)
    vscore = _row(cur, """
        SELECT v_score, v_band, owner_type
        FROM parcel_v_score WHERE parcelle_id = %(idu)s""", idu=idu)
    pm = _row(cur, """
        SELECT denomination, siren FROM parcelle_personne_morale WHERE idu = %(idu)s""", idu=idu)
    residuel = _row(cur, """
        SELECT sdp_residuelle_m2, sous_densite, taux_emprise_pct
        FROM parcel_residuel WHERE parcel_id = %(pid)s""", pid=pid)
    adresse = _row(cur, """
        SELECT numero, voie, code_postal FROM (
            SELECT a.numero, a.voie, a.code_postal FROM adresses a WHERE a.idu = %(idu)s
            UNION
            SELECT a.numero, a.voie, a.code_postal
            FROM adresse_parcelles ap JOIN adresses a ON a.id_ban = ap.id_ban
            WHERE ap.idu = %(idu)s
        ) t ORDER BY voie, numero NULLS LAST LIMIT 1""", idu=idu)
    dvf = _row(cur, """
        SELECT count(DISTINCT id_mutation)::int AS n_mutations, max(date_mutation) AS derniere
        FROM dvf_mutations_parcelle WHERE id_parcelle = %(idu)s""", idu=idu)
    if dvf and dvf["n_mutations"] == 0:
        dvf = None
    permis = _row(cur, """
        SELECT count(*)::int AS n, max(date)::date AS dernier
        FROM sitadel_permits WHERE idu_codes ? %(idu)s""", idu=idu)
    if permis and permis["n"] == 0:
        permis = None

    return {
        **head, "etage0_motifs": motifs, "zonage_plu": zonage, "risques": risques,
        "score_v2": v2, "vue_mer": vue_mer, "solaire": solar, "piscine": piscine,
        "dpe": dpe, "vegetation": vegetation, "copro_rnic": copro,
        "veille_succession": veille, "score_v": vscore, "proprietaire_moral": pm,
        "residuel": residuel, "adresse_ban": adresse, "dvf": dvf, "permis_sitadel": permis,
    }


def _get_json(url: str) -> tuple[dict | None, str | None]:
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:  # réseau/API down — remonté comme erreur de champ
        return None, str(e)


def collect_api(idu: str) -> dict:
    """Fiche de référence côté API — GET uniquement (fiche premium + score v2)."""
    fiche, err_f = _get_json(f"{API_BASE}/parcels/{idu}?source={RUN_LABEL}")
    v2, err_v = _get_json(f"{API_BASE}/v2/score/{idu}")

    out: dict[str, Any] = {}
    if fiche is None:
        out["fiche"] = {"erreur": err_f}
    else:
        zonage_detail = next((ln["detail"] for ln in fiche.get("lines", [])
                              if ln.get("layer") == "zonage_plu_gpu"), None)
        dvf_last = (fiche.get("dvf_parcelle") or {}).get("derniere_mutation") or {}
        out["fiche"] = {
            "commune": fiche.get("commune"),
            "surface_m2": fiche.get("surface_m2"),
            "statut": fiche.get("statut"),
            "etage0": fiche.get("etage0"),
            "q_score": fiche.get("q_score"), "a_score": fiche.get("a_score"),
            "a_completude": fiche.get("a_completude"),
            "completeness_score": fiche.get("completeness_score"),
            "score_v2": fiche.get("score_v2"),
            "evenement": fiche.get("evenement"),
            "zonage_detail": zonage_detail,
            "n_lignes_cascade": len(fiche.get("lines", [])),
            "score_v": ({"v_score": (fiche.get("score_v") or {}).get("v_score"),
                         "v_band": (fiche.get("score_v") or {}).get("v_band"),
                         "owner_type": (fiche.get("score_v") or {}).get("owner_type")}
                        if fiche.get("score_v") else None),
            "n_coproprietes": len(fiche.get("coproprietes") or []),
            "dvf_derniere_mutation": dvf_last.get("date_mutation"),
            "proprietaire_moral_siren": (fiche.get("proprietaire_moral") or {}).get("siren"),
        }
    if v2 is None:
        out["score_v2"] = {"erreur": err_v}
    else:
        out["score_v2"] = {
            "tier": v2.get("tier"), "rang": v2.get("rang"),
            "mult_base": v2.get("mult_base"), "percentile": v2.get("percentile"),
            "run_id": v2.get("run_id"), "model_version": v2.get("model_version"),
            "badge_veille_succession": (v2.get("badges") or {}).get("veille_succession"),
        }
    return out


def coherence_db_api(db: dict, api: dict) -> list[str]:
    """Contrôles de cohérence base↔API — chaque écart est une anomalie nommée."""
    pb: list[str] = []
    f, s2 = api.get("fiche", {}), api.get("score_v2", {})
    if "erreur" in f or "erreur" in s2:
        return [f"API inaccessible: fiche={f.get('erreur')} v2={s2.get('erreur')}"]

    def eq(label, a, b, tol=0.0):
        if a is None and b is None:
            return
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if abs(float(a) - float(b)) > tol:
                pb.append(f"{label}: db={a} api={b}")
        elif a != b:
            pb.append(f"{label}: db={a} api={b}")

    eq("statut (matrice)", db.get("matrice_statut"), f.get("statut"))
    eq("etage0", db.get("etage0"), f.get("etage0"))
    eq("surface_m2", db.get("surface_m2"), f.get("surface_m2"), tol=1)
    eq("commune", db.get("commune"), f.get("commune"))
    for k in ("q_score", "a_score", "a_completude", "completeness_score"):
        eq(k, db.get(k), f.get(k))
    dv2, fv2 = db.get("score_v2") or {}, f.get("score_v2") or {}
    eq("tier (db vs fiche)", dv2.get("tier"), fv2.get("tier"))
    eq("rang (db vs fiche)", dv2.get("rang"), fv2.get("rang"))
    eq("tier (db vs /v2/score)", dv2.get("tier"), s2.get("tier"))
    eq("rang (db vs /v2/score)", dv2.get("rang"), s2.get("rang"))
    eq("mult_base (db vs /v2/score)", dv2.get("mult_base"), s2.get("mult_base"), tol=0.011)
    eq("copro RNIC (db vs fiche)", (db.get("copro_rnic") or {}).get("n"), f.get("n_coproprietes"))
    eq("veille_succession (db vs badge /v2/score)",
       db.get("veille_succession") is not None, s2.get("badge_veille_succession"))
    eq("siren PM (db vs fiche)", (db.get("proprietaire_moral") or {}).get("siren"),
       f.get("proprietaire_moral_siren"))
    return pb


# ---------------------------------------------------------------- comparaison

def _flatten(prefix: str, obj: Any, out: dict[str, Any]) -> None:
    if isinstance(obj, dict):
        for k, v in sorted(obj.items()):
            _flatten(f"{prefix}.{k}" if prefix else k, v, out)
    elif isinstance(obj, list):
        out[prefix] = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    else:
        out[prefix] = obj


def compare_entry(expected: dict, actual: dict) -> list[str]:
    """Écarts champ par champ (chemins pointés), tolérances par suffixe."""
    exp, act = {}, {}
    _flatten("", expected, exp)
    _flatten("", actual, act)
    diffs = []
    for path in sorted(set(exp) | set(act)):
        e, a = exp.get(path, "<absent>"), act.get(path, "<absent>")
        if e == a:
            continue
        tol = next((t for suf, t in TOLERANCES.items() if path.endswith(suf)), None)
        if (tol is not None and isinstance(e, (int, float)) and isinstance(a, (int, float))
                and abs(float(e) - float(a)) <= tol):
            continue
        diffs.append(f"{path}: attendu={e!r} obtenu={a!r}")
    return diffs


def collect_all(idus: list[str], anchors: set[str] | None = None) -> dict:
    # Les ANCRES J3 ne gèlent que le couple base (statut cascade, tier v2) : PAS d'appel API pour
    # elles → on divise par ~3 le nombre de GET (piège rate-limit du golden élargi, cf. mémoire).
    anchors = anchors or set()
    with psycopg.connect(DB_URL, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute("SET default_transaction_read_only = on")
        v2run = served_v2_run(cur)
        entries = {}
        for idu in idus:
            db = collect_db(cur, idu, v2run)
            if idu in anchors:
                entries[idu] = {"db": db, "api": {}, "coherence_db_api": []}
                continue
            api = collect_api(idu)
            entries[idu] = {"db": db, "api": api,
                            "coherence_db_api": coherence_db_api(db, api)}
    return {
        "meta": {
            "mandat": "M6 Phase 1 §1.2 — golden dataset",
            "genere_le": datetime.now().isoformat(timespec="seconds"),
            "run_cascade": RUN_LABEL,
            "run_v2_servi": v2run,
            "api_base": API_BASE,
            "tolerances": TOLERANCES,
            "n_parcelles": len(entries),
        },
        "parcelles": entries,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--golden", default=DEFAULT_GOLDEN)
    ap.add_argument("--base-url", default=None,
                    help="cible QA (ex. https://vps:8010) — prime sur LABUSE_QA_TARGET/LABUSE_API_BASE")
    ap.add_argument("--dump", action="store_true",
                    help="imprime l'état courant (JSON) sur stdout au lieu de comparer")
    ap.add_argument("--idu", nargs="*", help="limiter aux parcelles données")
    args = ap.parse_args()
    if args.base_url:                       # P2 : override explicite de la cible
        global API_BASE
        API_BASE = args.base_url.rstrip("/")

    golden = None
    if not args.dump and os.path.exists(args.golden):
        with open(args.golden, encoding="utf-8") as f:
            golden = json.load(f)

    idus = args.idu or (list(golden["parcelles"]) if golden else GOLDEN_IDUS)
    anchors = {i for i, e in (golden or {}).get("parcelles", {}).items() if e.get("anchor")}
    current = collect_all(idus, anchors)

    if args.dump:
        json.dump(current, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    if golden is None:
        print(f"ERREUR: référence absente ({args.golden}) — générer avec --dump", file=sys.stderr)
        return 2

    ref_run = golden["meta"].get("run_v2_servi")
    cur_run = current["meta"].get("run_v2_servi")
    if ref_run != cur_run:
        print(f"WARN: run v2 servi a changé (référence={ref_run}, courant={cur_run}) — "
              f"écarts tier/rang attendus")

    n_fail, n_coh = 0, 0
    for idu in idus:
        exp = golden["parcelles"].get(idu)
        got = current["parcelles"][idu]
        if exp is None:
            print(f"FAIL {idu} — absente de la référence")
            n_fail += 1
            continue
        if exp.get("anchor"):
            # ANCRE J3 : on ne gèle QUE le couple (statut cascade, matrice, tier v2) + validation.
            # Robuste (aucun champ volatil) ; le tag `validation` pilote le gate boussole de l'arène.
            dbc = got["db"]
            cur_couple = {"cascade_status": dbc.get("cascade_status"),
                          "matrice_statut": dbc.get("matrice_statut"),
                          "tier_v2": (dbc.get("score_v2") or {}).get("tier")}
            diffs = [f"{k}: attendu={exp.get(k)!r} obtenu={cur_couple[k]!r}"
                     for k in cur_couple if exp.get(k) != cur_couple[k]]
            coh = got["coherence_db_api"]
            if coh:
                n_coh += 1
            if diffs:
                n_fail += 1
                print(f"FAIL {idu} [ancre {exp.get('validation')}] — {len(diffs)} écart(s)")
                for d in diffs:
                    print(f"     · {d}")
            else:
                print(f"PASS {idu} [ancre {exp.get('validation')} · {exp.get('motif') or exp.get('tier_v2')}]")
            continue
        diffs = compare_entry({"db": exp["db"], "api": exp["api"]},
                              {"db": got["db"], "api": got["api"]})
        coh = got["coherence_db_api"]
        if coh:
            n_coh += 1
        if diffs:
            n_fail += 1
            print(f"FAIL {idu} — {len(diffs)} écart(s)")
            for d in diffs:
                print(f"     · {d}")
        else:
            print(f"PASS {idu}" + (f"  [cohérence base↔API: {'; '.join(coh)}]" if coh else ""))

    print(f"\nBilan: {len(idus) - n_fail}/{len(idus)} PASS, {n_fail} FAIL, "
          f"{n_coh} parcelle(s) avec incohérence base↔API (runtime)")
    return 1 if n_fail else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERREUR: {exc}", file=sys.stderr)
        sys.exit(2)
