"""RADAR P5 · D2 — CYCLE DE VIE automatisé des biens du Radar. Rien ne se supprime, jamais.

Jobs (heure Indian/Reunion — les seuils comparent à la date Réunion, pas au fuseau serveur) :
  · quotidien  : `en_vente_longue` (> 90 j depuis publication) ; `a_reverifier` (> 60 j depuis la
                 dernière confirmation).
  · à chaque ingestion DVF : `vendue` — même parcelle **rattachement Sourcé UNIQUEMENT** + mutation
                 DVF dans [3 ; 18] mois après publication. Enregistre délai + écart prix affiché/acté
                 (l'écart n'est servi QUE sur un Sourcé, par construction).
  · mensuel    : `retiree_sans_vente` — la CIBLE Courrier.

GARDE CRITIQUE : `retiree_sans_vente` ne se déduit JAMAIS d'un lien mort. Un lien mort = `retiree`
(posé ailleurs, à la main). SEULE l'absence de mutation DVF sous 12 mois, sur un bien RATTACHÉ, qualifie.
Chaque changement de statut émet `pige.statut_change` ; une vente émet en plus `pige.vendue_dvf`.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .tables import EV_STATUT_CHANGE, EV_VENDUE_DVF, journaliser

# « aujourd'hui » à La Réunion, calculé en SQL (self-contained, indépendant du fuseau serveur).
_AUJ_REU = "(now() AT TIME ZONE 'Indian/Reunion')::date"
SEUIL_VENTE_LONGUE_J = 90
SEUIL_REVERIF_J = 60


def _basculer(db: Session, bien_id: int, nouveau: str, commune: str, motif: str) -> None:
    db.execute(text("UPDATE pige_biens SET statut = :s WHERE bien_id = :b"), {"s": nouveau, "b": bien_id})
    journaliser(db, EV_STATUT_CHANGE, f"Statut → {nouveau} — bien #{bien_id} ({commune})",
                detail=motif, dedup=f"pige:statut:{bien_id}:{nouveau}")


def marquer_en_vente_longue(db: Session) -> int:
    """> 90 j depuis la date de publication → en_vente_longue (depuis 'active')."""
    rows = db.execute(text(
        f"SELECT bien_id, commune FROM pige_biens WHERE statut = 'active' AND date_publication IS NOT NULL "
        f"AND date_publication < {_AUJ_REU} - {SEUIL_VENTE_LONGUE_J}")).mappings().all()
    for r in rows:
        _basculer(db, r["bien_id"], "en_vente_longue", r["commune"], f"> {SEUIL_VENTE_LONGUE_J} j en ligne")
    db.commit()
    return len(rows)


def marquer_a_reverifier(db: Session) -> int:
    """> 60 j depuis la dernière confirmation → a_reverifier (depuis active/en_vente_longue)."""
    rows = db.execute(text(
        f"SELECT bien_id, commune FROM pige_biens WHERE statut IN ('active','en_vente_longue') "
        f"AND date_derniere_confirmation < now() - interval '{SEUIL_REVERIF_J} days'")).mappings().all()
    for r in rows:
        _basculer(db, r["bien_id"], "a_reverifier", r["commune"], f"> {SEUIL_REVERIF_J} j sans confirmation")
    db.commit()
    return len(rows)


def matcher_dvf(db: Session) -> int:
    """`vendue` : rattachement SOURCÉ + mutation DVF « Vente » dans [3 ; 18] mois après publication.
    Enregistre le délai et l'écart prix affiché/acté (servi seulement sur Sourcé, garanti par le WHERE)."""
    cands = db.execute(text(
        "SELECT b.bien_id, b.idu, b.commune, b.date_publication, f.prix "
        "FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id "
        "WHERE b.rattachement_niveau = 'source' AND b.idu IS NOT NULL AND b.statut <> 'vendue' "
        "AND b.date_publication IS NOT NULL AND f.valide_at IS NOT NULL")).mappings().all()
    n = 0
    for c in cands:
        m = db.execute(text(
            "SELECT date_mutation, valeur_fonciere FROM dvf_mutations_parcelle "
            "WHERE id_parcelle = :idu AND nature_mutation ILIKE 'Vente%' "
            "AND date_mutation BETWEEN :pub + interval '3 months' AND :pub + interval '18 months' "
            "ORDER BY date_mutation LIMIT 1"),
            {"idu": c["idu"], "pub": c["date_publication"]}).mappings().first()
        if not m:
            continue
        delai = (m["date_mutation"] - c["date_publication"]).days
        valeur = int(m["valeur_fonciere"]) if m["valeur_fonciere"] is not None else None
        ecart = (c["prix"] - valeur) if (c["prix"] is not None and valeur is not None) else None
        db.execute(text(
            "UPDATE pige_biens SET statut = 'vendue', vendue_le = :d, vendue_valeur = :v, "
            "vendue_delai_j = :del, vendue_ecart_prix = :e WHERE bien_id = :b"),
            {"d": m["date_mutation"], "v": valeur, "del": delai, "e": ecart, "b": c["bien_id"]})
        detail = f"vendue {delai} j après publication" + (
            f" · écart affiché/acté {ecart:+d} €" if ecart is not None else "")
        journaliser(db, EV_STATUT_CHANGE, f"Statut → vendue — bien #{c['bien_id']} ({c['commune']})",
                    detail=detail, idu=c["idu"], dedup=f"pige:statut:{c['bien_id']}:vendue")
        journaliser(db, EV_VENDUE_DVF, f"Vendue (DVF) — bien #{c['bien_id']} ({c['commune']})",
                    detail=detail, idu=c["idu"], dedup=f"pige:vendue:{c['bien_id']}")
        n += 1
    db.commit()
    return n


def qualifier_retiree_sans_vente(db: Session) -> int:
    """Mensuel — la CIBLE Courrier. `retiree` + RATTACHÉE + retirée depuis > 12 mois + AUCUNE mutation
    DVF « Vente » depuis la publication → retiree_sans_vente. JAMAIS depuis un lien mort : le lien mort
    donne `retiree` (ailleurs), et sans idu on ne peut pas prouver l'absence de vente → on ne qualifie pas."""
    rows = db.execute(text(
        "SELECT bien_id, commune FROM pige_biens b WHERE b.statut = 'retiree' AND b.idu IS NOT NULL "
        "AND b.retiree_le IS NOT NULL AND b.retiree_le <= now() - interval '12 months' "
        "AND NOT EXISTS (SELECT 1 FROM dvf_mutations_parcelle m WHERE m.id_parcelle = b.idu "
        "                AND m.nature_mutation ILIKE 'Vente%' "
        "                AND (b.date_publication IS NULL OR m.date_mutation >= b.date_publication))")
    ).mappings().all()
    for r in rows:
        _basculer(db, r["bien_id"], "retiree_sans_vente", r["commune"],
                  "retirée > 12 mois, aucune vente DVF (cible Courrier)")
    db.commit()
    return len(rows)


def run_quotidien(db: Session) -> dict:
    return {"en_vente_longue": marquer_en_vente_longue(db), "a_reverifier": marquer_a_reverifier(db)}


def run_dvf(db: Session) -> dict:
    return {"vendue": matcher_dvf(db)}


def run_mensuel(db: Session) -> dict:
    return {"retiree_sans_vente": qualifier_retiree_sans_vente(db)}
