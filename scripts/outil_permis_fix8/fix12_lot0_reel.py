"""OUTIL-PERMIS-FIX-12 — LOT 0 : preuve des 4 faits de l'audit ASTRA-6 sur la base RÉELLE `labuse`.

Chaque fait est prouvé par CE QUE L'UTILISATEUR REÇOIT :
  1. veille de parcelle — on REJOUE la sélection EN LECTURE SEULE (comme l'audit) pour un suivi du
     01/01/2026 : la règle servie aujourd'hui (`date_depot >= since`) retient 9744012520010 et écarte
     97441626E0304 — l'INVERSE de l'événement réellement daté ;
  2. alerte de zone — `date_depot IS NOT NULL` rend inéligibles des permis géolocalisés qui ont une
     date d'AUTORISATION (compte : combien sont ainsi perdus) ;
  3. alerte ENREGISTRÉE 97441521G0020 — on LIT la ligne `alertes` servie : titre/détail/fait_date ;
  4. caducs — on appelle la ROUTE réelle GET /accueil/chiffres (`permis_caducs`) et on rejoue le
     filtre parcellaire (expression EXISTS de /parcels, app.py) pour 97401000AD0106.

Lecture seule : aucune écriture dans `labuse`. Sortie PASS/FAIL par fait ; exit 1 si un fait est FAIL.
Avant les correctifs (LOT 1) et avant les écritures autorisées (LOT 2/3), ce script est ROUGE.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse import permis_classe  # noqa: E402
from labuse.db import session_scope  # noqa: E402

SINCE = "2026-01-01"
VIEUX = "9744012520010"      # autorisé 24/10/2025 (AVANT le suivi) — faux dépôt 03/2026
RECENT = "97441626E0304"     # autorisé 03/08/2026 (DANS le suivi) — dépôt brut 2020
ALERTE_TEMOIN = "97441521G0020"   # autorisé 26/03/2021, dépôt 01/01/2021 (proxy, écarté)
PARC_CADUC = "97401000AD0106"

_echecs: list[str] = []


def _ok(cond: bool, titre: str, detail: str) -> None:
    etat = "PASS" if cond else "FAIL"
    if not cond:
        _echecs.append(titre)
    print(f"  [{etat}] {titre}\n         {detail}")


def _evenement_date_sql(a: str = "") -> str | None:
    """La date de l'événement réellement daté, VIA LA FONCTION UNIQUE du code (LOT 1). Absente avant
    le correctif → None → les faits 1/2 sont FAIL (rouge)."""
    fn = getattr(permis_classe, "evenement_date_sql", None)
    return fn(a) if fn else None


def fait_1_veille(s) -> None:
    print("\n① VEILLE DE PARCELLE — sélection sur l'événement réellement daté (suivi du 01/01/2026)")
    ev = _evenement_date_sql("")
    if ev is None:
        _ok(False, "permis_classe.evenement_date_sql absente", "fonction unique de sélection non encore livrée (LOT 1)")
        return
    rows = s.execute(text(
        f"""SELECT permit_id,
                   (date_depot >= :since)                         AS retenu_regle_actuelle,
                   (({ev}) >= :since)                              AS retenu_evenement_date,
                   date::date::text AS autorisation, date_depot::text AS depot
            FROM sitadel_permits WHERE permit_id IN (:a, :b)"""),
        {"since": SINCE, "a": VIEUX, "b": RECENT}).mappings().all()
    par = {r["permit_id"]: r for r in rows}
    if VIEUX in par:
        r = par[VIEUX]
        _ok(r["retenu_evenement_date"] is False,
            f"{VIEUX} ÉCARTÉ (autorisé {r['autorisation']} < {SINCE})",
            f"règle actuelle (date_depot {r['depot']}) retient={r['retenu_regle_actuelle']} ; "
            f"sur l'événement retient={r['retenu_evenement_date']}")
    else:
        _ok(False, f"{VIEUX} absent de sitadel_permits", "témoin introuvable")
    if RECENT in par:
        r = par[RECENT]
        _ok(r["retenu_evenement_date"] is True,
            f"{RECENT} RETENU (autorisé {r['autorisation']} ≥ {SINCE})",
            f"règle actuelle (date_depot {r['depot']}) retient={r['retenu_regle_actuelle']} ; "
            f"sur l'événement retient={r['retenu_evenement_date']}")
    else:
        _ok(False, f"{RECENT} absent de sitadel_permits", "témoin introuvable")


def fait_2_alerte_eligibilite(s) -> None:
    print("\n② ALERTE DE ZONE — un permis géolocalisé sans dépôt mais autorisé doit être éligible")
    ev = _evenement_date_sql("")
    n_perdus = s.execute(text(
        "SELECT count(*) FROM sitadel_permits "
        "WHERE geom IS NOT NULL AND date_depot IS NULL AND date IS NOT NULL")).scalar()
    if ev is None:
        _ok(False, f"{n_perdus} permis géolocalisés autorisés SANS dépôt — tous inéligibles",
            "la clé `date_depot IS NOT NULL` les exclut ; fonction unique de sélection non livrée (LOT 1)")
        return
    # éligibilité sur l'événement daté : COALESCE(depot_affichable, autorisation) IS NOT NULL
    n_eligibles = s.execute(text(
        f"SELECT count(*) FROM sitadel_permits "
        f"WHERE geom IS NOT NULL AND date_depot IS NULL AND date IS NOT NULL AND ({ev}) IS NOT NULL")).scalar()
    _ok(n_eligibles == n_perdus and n_perdus > 0,
        f"{n_perdus} permis géolocalisés autorisés SANS dépôt sont ÉLIGIBLES sur l'événement daté",
        f"éligibles sur l'événement : {n_eligibles}/{n_perdus} (la clé dépôt-non-nul ne les perd plus)")


def fait_3_alerte_enregistree(s) -> None:
    print(f"\n③ ALERTE ENREGISTRÉE {ALERTE_TEMOIN} — titre/détail/fait_date servis")
    row = s.execute(text(
        "SELECT label, payload->>'fait_date' fd, payload->>'detail' det "
        "FROM alertes WHERE source_ref = :p AND kind='permis_in_zone' LIMIT 1"),
        {"p": ALERTE_TEMOIN}).mappings().first()
    if row is None:
        _ok(False, f"alerte {ALERTE_TEMOIN} introuvable", "aucune ligne permis_in_zone")
        return
    lab = (row["label"] or "").lower()
    _ok("autorisé" in lab and "déposé" not in lab and row["fd"] == "2021-03-26",
        f"doit dire « Permis autorisé » au 2021-03-26",
        f"servi : label={row['label']!r} fait_date={row['fd']!r} detail={row['det']!r}")


def fait_4_caducs(s) -> None:
    print("\n④ CADUCS — route réelle GET /accueil/chiffres + filtre parcellaire")
    # (a) route réelle /accueil/chiffres
    try:
        from fastapi.testclient import TestClient
        from labuse.api import accueil as acc
        from labuse.api.app import app
        acc._cache["data"] = None   # neutralise le cache mémoire du compteur
        with TestClient(app) as cli:
            data = cli.get("/accueil/chiffres").json()
        pc = data.get("permis_caducs")
    except Exception as exc:  # noqa: BLE001
        pc = f"ERREUR route: {type(exc).__name__}: {exc}"
    _ok(pc == 4836, "GET /accueil/chiffres → permis_caducs == 4836", f"servi : {pc}")
    # (b) filtre parcellaire (expression EXISTS de /parcels signaux=permis_caduc, app.py)
    trouve = s.execute(text(
        "SELECT EXISTS (SELECT 1 FROM pc_caducs pcv WHERE pcv.idu = :i)"),
        {"i": PARC_CADUC}).scalar()
    _ok(trouve is True, f"filtre parcellaire permis_caduc trouve {PARC_CADUC}",
        f"EXISTS pc_caducs = {trouve}")


def diagnostic(s) -> None:
    print("\n— diagnostic (lecture seule) —")
    cond = permis_classe.depot_affichable_cond_sql("sp.")
    n_dep = s.execute(text("SELECT count(*) FROM alertes WHERE kind='permis_in_zone' AND label ILIKE '%déposé%'")).scalar()
    n_inval = s.execute(text(
        f"SELECT count(*) FROM alertes a JOIN sitadel_permits sp ON sp.permit_id=a.source_ref "
        f"WHERE a.kind='permis_in_zone' AND a.label ILIKE '%déposé%' AND NOT ({cond})")).scalar()
    n_perm = s.execute(text(
        f"SELECT count(DISTINCT a.source_ref) FROM alertes a JOIN sitadel_permits sp ON sp.permit_id=a.source_ref "
        f"WHERE a.kind='permis_in_zone' AND a.label ILIKE '%déposé%' AND NOT ({cond})")).scalar()
    caducs = s.execute(text("SELECT count(*) FROM pc_caducs")).scalar()
    print(f"  alertes permis_in_zone « déposé » : {n_dep} (dont dépôt INVALIDE : {n_inval}, "
          f"{n_perm} permis distincts)")
    print(f"  pc_caducs (table servie)          : {caducs}")


def main() -> int:
    with session_scope() as s:
        base = s.execute(text("SELECT current_database()")).scalar()
        print(f"Base : {base} (lecture seule)")
        if base != "labuse":
            print("  ⚠ base attendue 'labuse' — preuve non significative ailleurs")
        fait_1_veille(s)
        fait_2_alerte_eligibilite(s)
        fait_3_alerte_enregistree(s)
        fait_4_caducs(s)
        diagnostic(s)
    print("\n" + ("TOUT VERT" if not _echecs else f"ROUGE — {len(_echecs)} fait(s) FAIL : " + " · ".join(_echecs)))
    return 1 if _echecs else 0


if __name__ == "__main__":
    raise SystemExit(main())
