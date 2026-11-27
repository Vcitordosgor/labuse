"""Réutilisation des intersections cadastrales entre deux calculs de la fiche commune."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def assurer_cache(db: Session) -> None:
    existe = text("SELECT to_regclass('commune_exposition_cache') IS NOT NULL")
    if db.scalar(existe):
        return
    # Deux premiers lecteurs peuvent arriver avant le job nocturne.
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('labuse.commune_exposition_cache'))"))
    if not db.scalar(existe):
        db.execute(text("""
            CREATE TABLE commune_exposition_cache (
                commune text PRIMARY KEY, empreinte text NOT NULL,
                ppr_pct double precision, mvt_pct double precision,
                parc boolean NOT NULL, repli boolean NOT NULL
            )"""))


def _empreinte(db: Session, commune: str) -> str:
    # Version de chaque ligne MVCC, y compris pour les corrections de géométrie en place.
    # Le nœud physique change en cas de remplacement/réécriture de la table. On inclut
    # les couches limitrophes : une parcelle peut intersecter une zone de la commune voisine.
    # Le préfixe versionne le calcul des quatre champs conservés.
    return db.scalar(text("""
        SELECT concat_ws('/', '1', pg_relation_filenode('parcels'),
            pg_relation_filenode('spatial_layers'),
            (SELECT md5(string_agg(concat_ws(':',id,xmin,ctid), ',' ORDER BY id))
             FROM parcels WHERE commune = :c),
            (SELECT md5(string_agg(concat_ws(':',id,xmin,ctid), ',' ORDER BY id))
             FROM spatial_layers WHERE kind = 'ppr'
                 OR (kind = 'georisque_alea' AND subtype = 'mouvement_terrain')
                 OR (kind = 'parc_national' AND subtype = 'coeur')))
        """), {"c": commune})


def exposition(db: Session, commune: str, calcul):
    from ..communes import commune_known
    if not commune_known(nom=commune) or not db.scalar(text("SELECT to_regclass('commune_exposition_cache') IS NOT NULL")):
        return calcul(db, commune)
    cle = _empreinte(db, commune)
    ligne = db.execute(text("""
        SELECT ppr_pct, mvt_pct, parc, repli FROM commune_exposition_cache
        WHERE commune = :c AND empreinte = :cle
        """), {"c": commune, "cle": cle}).first()
    if ligne is not None:
        return tuple(ligne)
    valeurs = calcul(db, commune)
    # Sous READ COMMITTED, les quatre lectures peuvent chevaucher une ingestion.
    # Ne publier que le résultat d'un jeu de données stable.
    if _empreinte(db, commune) == cle:
        ppr, mvt, parc, repli = valeurs
        db.execute(text("""
            INSERT INTO commune_exposition_cache (commune, empreinte, ppr_pct, mvt_pct, parc, repli)
            VALUES (:c, :cle, :ppr, :mvt, :parc, :repli)
            ON CONFLICT (commune) DO UPDATE SET empreinte = excluded.empreinte,
                ppr_pct = excluded.ppr_pct, mvt_pct = excluded.mvt_pct,
                parc = excluded.parc, repli = excluded.repli
            """), {"c": commune, "cle": cle, "ppr": ppr, "mvt": mvt, "parc": parc, "repli": repli})
    return valeurs
