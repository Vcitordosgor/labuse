"""Ingestion Score V (Phases 1-2) — enrichissement propriétaires & annonces BODACC élargies.

Trois passes, toutes IDEMPOTENTES et RESUMABLES (cache en base, un identifiant déjà présent
n'est jamais re-requêté) :

  1. `fetch_owner_enrichment`   — recherche-entreprises PAR SIREN → `owner_enrichment`
     (état administratif, siège, NAF, dirigeants, catégorie juridique — payload brut).
  2. `fetch_denom_lookups`      — fallback §4.2 : dénominations DGFiP SANS SIREN valide →
     `owner_denom_lookup` (found / ambiguous / not_found) + cache candidat en owner_enrichment.
  3. `fetch_bodacc_annonces`    — BODACC 3 familles (PC + radiations + ventes-cessions) par
     SIREN propriétaire → `bodacc_annonces_owner`.

Périmètre : SIREN des groupes DGFiP marchands (0, 6, 7, 8, NULL). Les groupes publics
(1,2,3,4,9) et bailleurs (5) sont exclus : leur V est NULL par décision D4, aucun appel
API n'est nécessaire. La donnée d'abord, le score ensuite (moteur : scoring/score_v.py).
"""
from __future__ import annotations

import json
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..connectors.bodacc import BodaccConnector
from ..connectors.recherche_entreprises import (
    RechercheEntreprisesConnector,
    normalize_denomination,
    parse_result,
)

# Groupes DGFiP dont le V est NULL d'office (D4) : publics (1,2,3,4,9) + Office HLM (5).
GROUPES_V_NULL = (1, 2, 3, 4, 5, 9)
_GRP = ",".join(str(g) for g in GROUPES_V_NULL)


def eligible_sirens(session: Session) -> list[str]:
    """SIREN propriétaires à enrichir (marchands : groupes 0/6/7/8/NULL, SIREN bien formé)."""
    rows = session.execute(text(
        "SELECT DISTINCT regexp_replace(siren, '[^0-9]', '', 'g') FROM parcelle_personne_morale "
        f"WHERE siren ~ '^[0-9]{{9}}$' AND (groupe IS NULL OR groupe NOT IN ({_GRP})) "
        "ORDER BY 1")).all()
    return [r[0] for r in rows]


_UPSERT_ENRICH = text(
    "INSERT INTO owner_enrichment (siren, denomination, source, payload, fetched_at) "
    "VALUES (:siren, :denom, :source, CAST(:payload AS jsonb), now()) "
    "ON CONFLICT (siren) DO UPDATE SET denomination=EXCLUDED.denomination, "
    "  source=EXCLUDED.source, payload=EXCLUDED.payload, fetched_at=now()")


def fetch_owner_enrichment(session: Session, connector: RechercheEntreprisesConnector | None = None,
                           limit: int | None = None, log=print) -> dict:
    """Passe 1 — enrichit chaque SIREN propriétaire absent du cache. Commit par tranche de 200."""
    conn = connector or RechercheEntreprisesConnector()
    todo = [s for s in eligible_sirens(session)
            if not session.execute(text("SELECT 1 FROM owner_enrichment WHERE siren=:s"),
                                   {"s": s}).first()]
    if limit:
        todo = todo[:limit]
    log(f"owner_enrichment : {len(todo)} SIREN à requêter (cache déjà chaud pour le reste)")
    n_ok = n_miss = 0
    for i, siren in enumerate(todo, 1):
        rec = conn.fetch_by_siren(siren)
        if rec is None:
            # Miss cachée aussi (payload vide) : un SIREN inconnu ne sera pas re-requêté.
            session.execute(_UPSERT_ENRICH, {
                "siren": siren, "denom": None, "source": "recherche_entreprises",
                "payload": json.dumps({"not_found": True})})
            n_miss += 1
        else:
            parsed = parse_result(rec)
            session.execute(_UPSERT_ENRICH, {
                "siren": siren, "denom": parsed["denomination"],
                "source": "recherche_entreprises",
                "payload": json.dumps(rec, ensure_ascii=False)})
            n_ok += 1
        if i % 200 == 0:
            session.commit()
            log(f"  … {i}/{len(todo)}")
        time.sleep(conn.throttle_s)
    session.commit()
    return {"requetes": len(todo), "trouves": n_ok, "inconnus": n_miss}


def denominations_sans_siren(session: Session) -> list[str]:
    """Dénominations DGFiP distinctes des liens SANS SIREN valide (périmètre marchand)."""
    rows = session.execute(text(
        "SELECT DISTINCT denomination FROM parcelle_personne_morale "
        "WHERE (siren IS NULL OR siren !~ '^[0-9]{9}$') AND denomination <> '' "
        f"AND (groupe IS NULL OR groupe NOT IN ({_GRP})) ORDER BY 1")).all()
    return [r[0] for r in rows]


_UPSERT_LOOKUP = text(
    "INSERT INTO owner_denom_lookup (denomination_norm, status, siren, candidats, fetched_at) "
    "VALUES (:norm, :status, :siren, CAST(:cands AS jsonb), now()) "
    "ON CONFLICT (denomination_norm) DO UPDATE SET status=EXCLUDED.status, "
    "  siren=EXCLUDED.siren, candidats=EXCLUDED.candidats, fetched_at=now()")


def fetch_denom_lookups(session: Session, connector: RechercheEntreprisesConnector | None = None,
                        limit: int | None = None, log=print) -> dict:
    """Passe 2 — fallback dénomination : match EXACT sur dénomination normalisée (§4.2).

    1 candidat exact → found (+ fiche cachée en owner_enrichment) ; plusieurs → ambiguous
    (candidats bruts conservés, review queue peuplée au calcul) ; aucun → not_found."""
    conn = connector or RechercheEntreprisesConnector()
    cached = {r[0] for r in session.execute(
        text("SELECT denomination_norm FROM owner_denom_lookup")).all()}
    todo: list[tuple[str, str]] = []
    seen: set[str] = set()
    for denom in denominations_sans_siren(session):
        norm = normalize_denomination(denom)
        if not norm or norm in cached or norm in seen:
            continue
        seen.add(norm)
        todo.append((denom, norm))
    if limit:
        todo = todo[:limit]
    log(f"owner_denom_lookup : {len(todo)} dénominations à requêter")
    counts = {"found": 0, "ambiguous": 0, "not_found": 0}
    for i, (denom, norm) in enumerate(todo, 1):
        candidats = conn.search_by_name(norm)
        exacts = [c for c in candidats
                  if normalize_denomination(c.get("nom_raison_sociale") or c.get("nom_complet")) == norm]
        if len(exacts) == 1:
            c = exacts[0]
            session.execute(_UPSERT_LOOKUP, {
                "norm": norm, "status": "found", "siren": c.get("siren"), "cands": None})
            session.execute(_UPSERT_ENRICH, {
                "siren": c.get("siren"), "denom": parse_result(c)["denomination"],
                "source": "recherche_entreprises", "payload": json.dumps(c, ensure_ascii=False)})
            counts["found"] += 1
        elif len(exacts) > 1:
            slim = [{"siren": c.get("siren"), "nom": c.get("nom_complet"),
                     "commune_siege": (c.get("siege") or {}).get("libelle_commune")}
                    for c in exacts]
            session.execute(_UPSERT_LOOKUP, {
                "norm": norm, "status": "ambiguous", "siren": None,
                "cands": json.dumps(slim, ensure_ascii=False)})
            counts["ambiguous"] += 1
        else:
            session.execute(_UPSERT_LOOKUP, {
                "norm": norm, "status": "not_found", "siren": None, "cands": None})
            counts["not_found"] += 1
        if i % 200 == 0:
            session.commit()
            log(f"  … {i}/{len(todo)}")
        time.sleep(conn.throttle_s)
    session.commit()
    return counts


def matched_owner_sirens(session: Session) -> list[str]:
    """SIREN à interroger au BODACC = directs (marchands) + résolus par dénomination."""
    direct = set(eligible_sirens(session))
    fallback = {r[0] for r in session.execute(text(
        "SELECT DISTINCT siren FROM owner_denom_lookup WHERE status='found' AND siren IS NOT NULL")).all()}
    return sorted(direct | fallback)


_UPSERT_BODACC = text(
    "INSERT INTO bodacc_annonces_owner (id, siren, famille, nature, date_annonce, payload, fetched_at) "
    "VALUES (:id, :siren, :famille, :nature, :date_annonce, CAST(:payload AS jsonb), now()) "
    "ON CONFLICT (id) DO UPDATE SET famille=EXCLUDED.famille, nature=EXCLUDED.nature, "
    "  date_annonce=EXCLUDED.date_annonce, payload=EXCLUDED.payload, fetched_at=now()")


def fetch_bodacc_annonces(session: Session, connector: BodaccConnector | None = None,
                          log=print) -> int:
    """Passe 3 — annonces BODACC (PC/radiations/ventes) des SIREN propriétaires.

    Une annonce peut porter plusieurs SIREN (vente : acheteur + vendeur) → une ligne par
    (annonce, SIREN propriétaire concerné), id = « <annonce_id>:<siren> ». Idempotent."""
    conn = connector or BodaccConnector()
    owners = matched_owner_sirens(session)
    log(f"bodacc_annonces_owner : interrogation de {len(owners)} SIREN (3 familles, batché ×40)")
    owner_set = set(owners)
    n = 0
    for parsed in conn.fetch_score_v_by_sirens(owners):
        for siren in parsed["sirens"]:
            if siren not in owner_set:
                continue  # SIREN tiers d'une annonce multi-parties (ex. acheteur non propriétaire)
            session.execute(_UPSERT_BODACC, {
                "id": f"{parsed['annonce_id']}:{siren}", "siren": siren,
                "famille": parsed["famille"], "nature": (parsed["nature"] or "")[:200] or None,
                "date_annonce": parsed["date_annonce"],
                "payload": json.dumps(parsed["raw"], ensure_ascii=False)})
            n += 1
        if n and n % 200 == 0:
            session.commit()
            log(f"  … {n} annonces")
    session.commit()
    return n
