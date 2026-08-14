"""M73-B Volet C — LE point d'appel UNIQUE du marché (DVF + permis) pour les documents.

Un seul endroit où les documents LISENT le marché. Arbitrage Vic (M73-B) : « un point d'appel,
paramètres NOMMÉS » — chaque document garde ses paramètres (via un `profil`), le CALCUL n'est PAS
touché (délégation aux calculs historiques). Écart au « même chiffre » ASSUMÉ par Vic : on préserve
les doctrines M38 (voisinage 100 m) et M79 (prix terrain) plutôt que de fusionner de force.

Ce module est le point que `MANDAT_DVF` éditera : quand le calcul sera corrigé ICI (ou dans les calculs
délégués), les documents suivront automatiquement — ils ne connaissent que `marche_dvf` / `permits`.

Les `profil` sont PROVISOIRES et NOMMÉS (renvoi MANDAT_DVF) : ils encapsulent les trois lectures
historiques distinctes sans les fusionner.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# ── Profils DVF (paramètres provisoires — cf. MANDAT_DVF) ─────────────────────────────────────────
DVF_SECTEUR_DOSSIER = "secteur_dossier"        # 500 m / 3 ans, bâti + terrain nu (flash/_marche)
DVF_BANQUIER_ADAPTATIF = "banquier_adaptatif"  # rayon adaptatif 500→1500→commune, Q1/méd/Q3 (bilan/sector_price)
DVF_VOISINAGE_100M = "voisinage_100m"          # < 100 m / 36 mois, doctrine M38 (site_voisinage)

# ── Profils PERMIS (paramètres provisoires — cf. MANDAT_DVF) ──────────────────────────────────────
PERMITS_FLASH_500M = "flash_500m"              # 500 m / 24 mois (ingestion/permits.nearby_permits)
PERMITS_FICHE_36M = "fiche_36m"                # parcelle + secteur, 36 mois (ingestion/permits.depots_recents)
PERMITS_VOISINAGE_100M = "voisinage_100m"      # < 100 m / 36 mois, doctrine M38 (site_voisinage)


def _parcel_id(db: Session, idu: str) -> int | None:
    return db.execute(text("SELECT id FROM parcels WHERE idu = :idu"), {"idu": idu}).scalar()


def marche_dvf(db: Session, idu: str, *, profil: str, avail: set[str] | None = None) -> dict | None:
    """Lecture DVF d'une parcelle, par le point d'appel UNIQUE. `profil` = préset de paramètres nommé
    (provisoire, MANDAT_DVF). Délègue au calcul existant — aucun recalcul, aucun chiffre changé ici."""
    if profil == DVF_SECTEUR_DOSSIER:
        from .flash.data import _marche
        if avail is None:                       # le dossier fournit déjà `avail` ; sinon on le résout
            from .flash.data import _existing_tables, _NEEDED_TABLES
            avail = _existing_tables(db, _NEEDED_TABLES)
        return _marche(db, idu, avail)
    if profil == DVF_BANQUIER_ADAPTATIF:
        from .faisabilite.bilan import sector_price
        from .faisabilite.engine import Hypotheses
        pid = _parcel_id(db, idu)
        return sector_price(db, pid, Hypotheses.charger()) if pid else None
    if profil == DVF_VOISINAGE_100M:
        from .api.site_voisinage import voisinage_proche
        return voisinage_proche(db, idu)
    raise ValueError(f"profil DVF inconnu : {profil!r}")


def permits(db: Session, idu: str, *, profil: str) -> dict | None:
    """Lecture des permis (SITADEL) d'une parcelle, par le point d'appel UNIQUE. `profil` = préset de
    paramètres nommé (provisoire, MANDAT_DVF). Délègue au calcul existant — aucun recalcul."""
    if profil == PERMITS_FLASH_500M:
        from .ingestion.permits import nearby_permits
        pid = _parcel_id(db, idu)
        return nearby_permits(db, pid) if pid else None
    if profil == PERMITS_FICHE_36M:
        from .ingestion.permits import depots_recents
        pid = _parcel_id(db, idu)
        return depots_recents(db, pid) if pid else None
    if profil == PERMITS_VOISINAGE_100M:
        from .api.site_voisinage import voisinage_proche
        return voisinage_proche(db, idu)          # le voisinage porte DVF ET permis dans un seul dict
    raise ValueError(f"profil permis inconnu : {profil!r}")
