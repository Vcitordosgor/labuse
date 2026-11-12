"""DEPLOY-GROUPE-3 — enrich scénarios V2 de q_v23 depuis la reconstruction PERSISTÉE de seq 18.

Au lieu de recalculer `compute_residuel` LIVE (≈210 ms/parcelle → ~28 h sur l'île), on substitue SA
SORTIE par les colonnes DÉJÀ persistées de seq 18 : C=`sdp_max_m2`, E=`sdp_existante_m2`,
R=`sdp_residuelle_m2`, `cause`, `assiette_source`. Prouvé égal au live À L'UNITÉ en amont
(`sdp_max_m2 - sdp_existante_m2 == d_net_m2` : 0 écart / 272 425 ; quantités live == seq 18 :
0 écart / 1 453). La LOGIQUE scénario (bande / statut / horizon / zone) est INCHANGÉE — seule la
SOURCE de C/E/R change ; `zone_dominante` reste live (13 ms/parcelle). Les champs `_precis`
(non arrondis) ne sont PAS persistés dans seq 18 → on ne les fournit pas (le builder retombe sur
l'arrondi ; condition 5 de Vic — champ absent, jamais inventé). Écrit UNIQUEMENT le run candidat
q_v23 (+ labels temporaires de preuve, nettoyés). q_v20 servi n'est JAMAIS touché. Idempotent (upsert).

Modes :
  prove <N>   preuve d'équivalence (condition 3) : N parcelles au hasard + témoins, batch seq18 vs
              batch live, 0 écart requis ; exit 1 au moindre écart (→ on passe en B, pas en C).
  announce    nombre de lignes + taille estimée écrite (condition 2), par cause pour les non-reconstruits.
  run         enrichit q_v23 sur toute l'île (chunké, upsert).
Usage : LABUSE_RESIDUEL_RUN_SEQ=18 python scripts/q23_scenarios_enrich_seq18.py <mode> [N]
"""
from __future__ import annotations
import sys
import time
from labuse.db import session_scope
from sqlalchemy import text
import labuse.faisabilite.residuel as _resid
from labuse.scoring import scenarios_v2_persist as P

RUN = "q_v23"
TEMOINS = [
    "97411000BZ1065", "97409000AK0804", "97415000DH0076",      # bâti / terrain / copro
    "97418000AY0416", "97411000DK0447", "97415000CW0252",      # exigu → régain
    "97419000AN0398", "97403000AL0258",                        # exigu confirmé / à vérifier
]

_SEQ18: dict[int, tuple] = {}
_orig_compute_residuel = _resid.compute_residuel


def _load_seq18(s, ids=None) -> None:
    q = ("SELECT parcel_id, cause, sdp_max_m2, sdp_existante_m2, sdp_residuelle_m2, assiette_source "
         "FROM parcel_residuel_runs WHERE run_seq=18")
    params: dict = {}
    if ids is not None:
        q += " AND parcel_id = ANY(:ids)"
        params["ids"] = list(ids)
    for pid, cause, cmax, cex, cres, asrc in s.execute(text(q), params):
        _SEQ18[pid] = (cause, cmax, cex, cres, asrc)


def _fake_residuel(session, parcel_id, faisa=None):
    """Sortie de compute_residuel reconstruite depuis seq 18 (SANS les champs _precis : condition 5).
    Le builder lit exactement 7 champs ; tous proviennent de colonnes persistées ou d'une dérivation
    déterministe (disponible = cause IS NULL)."""
    row = _SEQ18.get(parcel_id)
    if row is None:
        return _orig_compute_residuel(session, parcel_id, faisa)   # non préchargé → live (ne doit pas arriver en run)
    cause, cmax, cex, cres, asrc = row
    if cause is None:                                              # constructible (compute_residuel: disponible=True)
        return {"disponible": True, "sdp_max_m2": cmax, "sdp_existante_m2": cex,
                "sdp_residuelle_m2": cres, "assiette_source": asrc}
    return {"disponible": False, "cause": cause, "sdp_ecrite": cres, "assiette_source": asrc}


def _patch():
    _resid.compute_residuel = _fake_residuel


def _unpatch():
    _resid.compute_residuel = _orig_compute_residuel


_CMP_COLS = ("scenario", "status", "cause", "band", "score", "band_provisional",
             "additional_m2", "project_total_m2", "existing_m2", "net_signed_m2",
             "conditional_future_m2", "residual_m2", "zone_prod_zone", "zone_prod_area_m2",
             "vigilance", "bande_v1", "enriched", "assiette_source", "surface_m2")


def _prove(n: int) -> int:
    with session_scope() as s:
        P.ensure_table(s)
        rnd = [r[0] for r in s.execute(text(
            "SELECT parcel_id FROM score_labuse WHERE run_label=:r ORDER BY md5(parcel_id::text) LIMIT :n"),
            {"r": RUN, "n": n})]
        tem = [r[0] for r in s.execute(text(
            "SELECT id FROM parcels WHERE idu = ANY(:t)"), {"t": TEMOINS})]
        ids = sorted(set(rnd) | set(tem))
        print(f"[prove] {len(ids)} parcelles ({len(rnd)} au hasard + {len(tem)} témoins)", flush=True)
        _load_seq18(s, ids)
        L_S18, L_LIVE = RUN + "_prv_s18", RUN + "_prv_live"
        for lbl in (L_S18, L_LIVE):
            s.execute(text("DELETE FROM parcel_scenario_v2_runs WHERE run_label=:l"), {"l": lbl})
        s.commit()
        # batch depuis seq 18 (patché)
        _patch()
        P.compute_scenarios_v2_batch(s, ids, run_label=L_S18, enrich=True)
        # batch live (réel)
        _unpatch()
        P.compute_scenarios_v2_batch(s, ids, run_label=L_LIVE, enrich=True)
        # comparaison ligne à ligne (toutes colonnes substantielles)
        cols = ", ".join(_CMP_COLS)
        a = {(r.parcel_id, r.scenario): r for r in s.execute(text(
            f"SELECT parcel_id, {cols} FROM parcel_scenario_v2_runs WHERE run_label=:l"), {"l": L_S18})}
        b = {(r.parcel_id, r.scenario): r for r in s.execute(text(
            f"SELECT parcel_id, {cols} FROM parcel_scenario_v2_runs WHERE run_label=:l"), {"l": L_LIVE})}
        ecarts = []
        for k in sorted(set(a) | set(b)):
            ra, rb = a.get(k), b.get(k)
            if ra is None or rb is None:
                ecarts.append((k, "ABSENT", "s18" if ra is None else "live", None)); continue
            for c in _CMP_COLS:
                if getattr(ra, c) != getattr(rb, c):
                    ecarts.append((k, c, getattr(ra, c), getattr(rb, c)))
        # nettoyage des labels temporaires
        for lbl in (L_S18, L_LIVE):
            s.execute(text("DELETE FROM parcel_scenario_v2_runs WHERE run_label=:l"), {"l": lbl})
        s.commit()
        print(f"[prove] lignes comparées : s18={len(a)} live={len(b)} · ÉCARTS={len(ecarts)}", flush=True)
        for e in ecarts[:25]:
            print("   ✗", e, flush=True)
        if ecarts:
            print("[prove] ÉCART DÉTECTÉ → arrêt. On passe en B, pas en C (condition 3 Vic).", flush=True)
            return 1
        print("[prove] ✓ IDENTIQUE À L'UNITÉ (seq18 == live) sur toutes les lignes et colonnes.", flush=True)
        return 0


def _announce() -> int:
    with session_scope() as s:
        nlignes = s.execute(text("SELECT count(*) FROM parcel_scenario_v2_runs WHERE run_label=:r"),
                            {"r": RUN}).scalar()
        taille = s.execute(text("SELECT pg_size_pretty(pg_total_relation_size('parcel_scenario_v2_runs'))")).scalar()
        # non-reconstruits dans seq 18 = parcelles à cause (jamais un zéro) — compte par cause (condition 4)
        print(f"[announce] run q_v23 : {nlignes} lignes (2 scénarios × 433 229). L'enrich REMPLIT des "
              f"colonnes (upsert), n'ajoute pas de lignes → taille ~stable (table actuelle : {taille}).", flush=True)
        print("[announce] parcelles SANS reconstruction dans seq 18 (cause portée, jamais 0) — compte par cause :",
              flush=True)
        for cause, n in s.execute(text(
                "SELECT cause, count(*) FROM parcel_residuel_runs WHERE run_seq=18 AND cause IS NOT NULL "
                "GROUP BY cause ORDER BY 2 DESC")):
            print(f"    {cause:28s} {n}", flush=True)
    return 0


def _run() -> int:
    with session_scope() as s:
        P.ensure_table(s)
        ids = [r[0] for r in s.execute(text(
            "SELECT parcel_id FROM score_labuse WHERE run_label=:r ORDER BY parcel_id"), {"r": RUN})]
        print(f"[run] {len(ids)} parcelles — enrich depuis seq 18…", flush=True)
        _load_seq18(s)
        _patch()
        t = time.time()
        b = P.compute_scenarios_v2_batch(s, ids, run_label=RUN, enrich=True,
                                         log=lambda m: print("  " + m, flush=True))
        _unpatch()
        dt = time.time() - t
        n_enr = s.execute(text("SELECT count(*) FROM parcel_scenario_v2_runs WHERE run_label=:r AND enriched=true"),
                          {"r": RUN}).scalar()
        n_cp = s.execute(text("SELECT count(*) FROM parcel_scenario_v2_runs WHERE run_label=:r AND status='COMPUTE_PENDING'"),
                         {"r": RUN}).scalar()
        print(f"[run] FAIT : {b['parcelles']} parc · {int(dt)}s · enriched={n_enr} · reste COMPUTE_PENDING={n_cp}",
              flush=True)
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "announce"
    if mode == "prove":
        return _prove(int(sys.argv[2]) if len(sys.argv) > 2 else 500)
    if mode == "announce":
        return _announce()
    if mode == "run":
        return _run()
    print(f"mode inconnu : {mode} (prove <N> | announce | run)")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
