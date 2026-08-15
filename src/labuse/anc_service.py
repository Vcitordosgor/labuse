"""M88 — L'ASSAINISSEMENT SERVI à la fiche. POINT DE CALCUL UNIQUE (fiche écran, PDF, export).

Trois états, jamais quatre, et AUCUN seuil, AUCUNE bascule (M88 a retiré l'Estimé `proba_anc`) :
  · Sourcé           — `zone_anc` réglementaire (collectif | ANC) + commune (source : zonage GPU) ;
  · Sourcé (secteur) — zonage absent MAIS taux INSEE de non-raccordement du SECTEUR (RP2022, variable
                       EGOUL, maille IRIS, repli commune). On affiche le TAUX, jamais un verdict :
                       « Dans ce secteur, X % des logements ne sont pas raccordés au réseau collectif. »
                       Pas de « probablement », pas de seuil — le lecteur conclut, pas nous. Un taux bas
                       n'est JAMAIS un feu vert au raccordement. La maille ET le millésime sont dits ;
  · Absent           — ni zonage ni taux de secteur → « zonage non disponible » (un NULL n'est pas un
                       raccordement).

M88 : `proba_anc` n'est plus lu ici (mesuré hors domaine — précision plafonnée à 34 %, calculée sur
l'urbain zoné alors que l'Estimé servait le rural ; cf. docs/audits/AUDIT_M88_ANC_SECTEUR.md). La table
`parcel_anc` et son job sont CONSERVÉS (le champ `zone_anc` reste lu ci-dessous, et `proba_anc` garde un
usage interne — signal `anc_mutation`), mais ne fabriquent plus l'affichage. Le taux servi est le taux
BRUT (`anc_maille_taux.taux_non_racc`), sans bonus rural, sans borne, sans seuil.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def statut_anc(db: Session, idu: str) -> dict:
    """L'état ANC SERVI d'une parcelle. Retourne TOUJOURS un dict (Absent est un état, pas un trou)."""
    # M90 — garde défensive AU POINT UNIQUE (cohérente avec le garde secteur plus bas) : sur une base
    # sans la table `parcel_anc` (data-gap, base de test, base fraîche), on ne plante PAS une fiche en
    # 500 — ce serait une panne d'environnement déguisée en régression. Table absente → zone introuvable
    # (None) → on retombe sur secteur puis Absent (un état, jamais un crash). L'absence de la COLONNE
    # `zone_anc`, elle, resterait levée : une régression de schéma ne doit pas se cacher derrière ce garde.
    zone = None
    if db.execute(text("SELECT to_regclass('parcel_anc')")).scalar() is not None:
        zone = db.execute(text("SELECT zone_anc FROM parcel_anc WHERE idu = :idu"), {"idu": idu}).scalar()
    commune = db.execute(text("SELECT commune FROM parcels WHERE idu = :idu"), {"idu": idu}).scalar()

    if zone:                                                       # ── SOURCÉ (réglementaire) ──
        est_anc = zone == "anc"
        return {
            "statut": "source",
            "libelle": "Assainissement non collectif" if est_anc else "Tout-à-l'égout (collectif)",
            "anc": est_anc,
            "phrase": (f"Zonage réglementaire à {commune} : "
                       + ("assainissement non collectif — surface d'épandage et étude de sol requises."
                          if est_anc else "raccordement au tout-à-l'égout (collectif).")),
            "source": "Zonage d'assainissement (Géoportail de l'urbanisme / GPU)",
            "commune": commune,
        }

    # ── SOURCÉ (SECTEUR) : taux BRUT RP2022, IRIS d'abord (maille fine), repli commune. Rattachement
    # spatial par centroïde (spatial_layers kind='iris_insee'), jamais proba_anc. Un seul endroit. ──
    # Garde défensive : sur une base sans ingestion ANC (tables absentes), on ne plante pas une fiche —
    # le secteur est simplement introuvable → Absent (un état, pas un crash).
    tables_ok = db.execute(text(
        "SELECT to_regclass('anc_maille_taux') IS NOT NULL "
        "  AND to_regclass('spatial_layers') IS NOT NULL")).scalar()
    sect = None if not tables_ok else db.execute(text(
        "SELECT round(t.taux_non_racc)::int AS taux, t.millesime, sl.name AS nom "
        "FROM parcels p "
        "JOIN spatial_layers sl ON sl.kind = 'iris_insee' "
        "  AND ST_Contains(sl.geom_2975, ST_Centroid(p.geom_2975)) "
        "JOIN anc_maille_taux t ON t.maille = 'iris' AND t.code = sl.subtype "
        "WHERE p.idu = :idu LIMIT 1"), {"idu": idu}).mappings().first()
    maille_type = "iris"
    if tables_ok and not sect:                                     # repli commune (IRIS non diffusé)
        sect = db.execute(text(
            "SELECT round(t.taux_non_racc)::int AS taux, t.millesime "
            "FROM anc_maille_taux t WHERE t.maille = 'commune' AND t.insee = left(:idu, 5) LIMIT 1"),
            {"idu": idu}).mappings().first()
        maille_type = "commune"

    if sect and sect["taux"] is not None:
        taux = int(sect["taux"])
        mille = sect["millesime"] or "RP2022"
        nom = sect.get("nom")
        if maille_type == "iris" and nom:
            maille_txt, intro, grain = f"secteur IRIS « {nom} »", f"Dans ce secteur IRIS « {nom} »", "IRIS"
        elif maille_type == "commune":
            maille_txt, intro, grain = f"commune de {commune}", f"Dans la commune de {commune}", "commune"
        else:
            maille_txt, intro, grain = "secteur", "Dans ce secteur", "secteur"
        return {
            "statut": "source_secteur",
            "libelle": f"{taux} % des logements du secteur ne sont pas raccordés au réseau collectif",
            "taux_non_racc": taux,
            "maille": maille_txt,
            "maille_type": maille_type,
            "millesime": mille,
            "phrase": (f"{intro}, {taux} % des logements ne sont pas raccordés au réseau collectif "
                       f"(INSEE {mille}). C'est un taux de SECTEUR, pas l'état de cette parcelle. "
                       f"À vérifier auprès du SPANC."),
            "source": f"INSEE {mille} — variable EGOUL, agrégée par {grain}",
        }

    return {                                                        # ── ABSENT ──
        "statut": "absent",
        "libelle": "Zonage non disponible",
        "phrase": ("Zonage d'assainissement non disponible sur cette commune "
                   "(réglementaire absent, secteur non renseigné). Ce n'est pas un raccordement présumé."),
    }


def couverture_anc(db: Session) -> dict:
    """Couverture réglementaire = communes ayant un zonage (pour DIRE l'Absent, pas le subir). Calculé,
    jamais en dur : sur 24 communes, le zonage réglementaire SIG n'existe que pour une minorité."""
    # M90 — même garde défensive : table absente (data-gap) → couverture 0 (l'absence honnête), pas un 500.
    avec = 0
    if db.execute(text("SELECT to_regclass('parcel_anc')")).scalar() is not None:
        avec = db.execute(text("SELECT count(DISTINCT left(idu, 5)) FROM parcel_anc WHERE zone_anc IS NOT NULL")).scalar() or 0
    total = db.execute(text("SELECT count(DISTINCT commune) FROM parcels")).scalar() or 0
    return {"communes_avec_zonage": int(avec), "communes_total": int(total)}
