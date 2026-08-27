"""L1 (rattrapage KelFoncier 2) — HISTORIQUE du propriétaire personne morale par millésime.

Lit la table versionnée `pm_proprietaires_millesimes` (millésimes DGFiP 2019→2024, Licence
Ouverte 2.0, situation au 1ᵉʳ janvier) UNIE au millésime SERVI 2025 (`parcelle_personne_morale`,
JAMAIS écrasé — lecture seule). Le millésime est une COLONNE, pas un écrasement.

Doctrine (mandat) :
  · Le diff est un CONSTAT, jamais une interprétation. « La parcelle est passée de la SCI A à la
    SCI B entre 2023 et 2024 » : oui. « La SCI B prépare une opération » : non.
  · RGPD : ces fichiers ne portent QUE des personnes morales. Aucune personne physique n'entre ici.
  · Hors scoring : l'historique s'affiche, il ne pondère rien.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

SOURCE = "DGFiP — parcelles des personnes morales (millésimes annuels, Licence Ouverte 2.0)"

# Millésime servi (table de prod), ajouté à la volée SI la table versionnée ne le porte pas encore
# (KF-101 : l'ingestion M2 précède la publication amont du 2025). Le NOT EXISTS évite tout doublon
# le jour où un 2025 versionné serait ingéré.
_MILLESIME_SERVI = 2025

# Situation au 1ᵉʳ janvier de l'année (date sémantique de chaque source, affichée en fiche).
def situation_le(millesime: int) -> str:
    return f"1ᵉʳ janvier {millesime}"


_TIMELINE_SQL = text("""
WITH unifie AS (
    SELECT millesime, idu, siren, denomination, forme_juridique, groupe_label
    FROM pm_proprietaires_millesimes
    UNION ALL
    SELECT :servi, idu, siren, denomination, forme_juridique, groupe_label
    FROM parcelle_personne_morale
    WHERE NOT EXISTS (SELECT 1 FROM pm_proprietaires_millesimes WHERE millesime = :servi)
)
SELECT millesime, siren, denomination, forme_juridique, groupe_label
FROM unifie WHERE idu = :idu ORDER BY millesime
""")


def historique(db: Session, idu: str) -> dict | None:
    """Timeline propriétaire PM + changements CONSTATÉS, pour la fiche parcelle.

    Retourne None si la parcelle n'a AUCUN millésime PM (elle n'a jamais eu de propriétaire moral
    connu — on n'affiche rien plutôt qu'un bloc vide). RGPD : PM uniquement, par construction.
    """
    rows = [dict(r) for r in db.execute(
        _TIMELINE_SQL, {"idu": idu, "servi": _MILLESIME_SERVI}).mappings().all()]
    if not rows:
        return None

    millesimes = [{
        "millesime": r["millesime"],
        "situation": situation_le(r["millesime"]),
        "siren": r["siren"],
        "denomination": r["denomination"],
        "forme_juridique": r["forme_juridique"],
        "groupe": r["groupe_label"],
    } for r in rows]

    # Changements = transitions consécutives où le SIREN diffère. CONSTAT brut (avant → après),
    # aucune interprétation. On compare le SIREN (identité juridique) ; à défaut la dénomination.
    changements: list[dict] = []
    for prev, cur in zip(rows, rows[1:]):
        a, b = prev.get("siren"), cur.get("siren")
        change = (a or "") != (b or "") if (a or b) else (
            (prev.get("denomination") or "") != (cur.get("denomination") or ""))
        if change:
            changements.append({
                "de_millesime": prev["millesime"],
                "a_millesime": cur["millesime"],
                "siren_avant": prev.get("siren"),
                "denomination_avant": prev.get("denomination"),
                "siren_apres": cur.get("siren"),
                "denomination_apres": cur.get("denomination"),
            })

    return {
        "source": SOURCE,
        "millesimes": millesimes,
        "n_millesimes": len(millesimes),
        "changements": changements,
        "n_changements": len(changements),
        # garde-fou de lecture (KF-102) : un changement n'est PAS une vente prouvée ; les premiers
        # millésimes ont une complétude SIREN croissante côté source.
        "note": "Constat de la source DGFiP (situation au 1ᵉʳ janvier). Un changement de propriétaire "
                "moral n'affirme pas une vente ; ce n'est pas un signal de scoring.",
    }


def acquisitions_recentes(db: Session, commune_insee: str, depuis_millesime: int = 2022,
                          limit: int = 200) -> dict:
    """« Acquisitions récentes par secteur » — changements de PM propriétaire dans une commune,
    du plus récent au plus ancien. CONSTAT sourcé, hors scoring. `commune_insee` = code INSEE 5c.
    """
    sql = text("""
    WITH unifie AS (
        SELECT millesime, idu, siren, denomination
        FROM pm_proprietaires_millesimes WHERE left(idu, 5) = :insee
        UNION ALL
        SELECT :servi, idu, siren, denomination
        FROM parcelle_personne_morale
        WHERE left(idu, 5) = :insee
          AND NOT EXISTS (SELECT 1 FROM pm_proprietaires_millesimes WHERE millesime = :servi)
    ),
    paires AS (
        SELECT a.idu,
               a.millesime AS de_m, a.siren AS s_av, a.denomination AS d_av,
               b.millesime AS a_m,  b.siren AS s_ap, b.denomination AS d_ap
        FROM unifie a JOIN unifie b
          ON b.idu = a.idu AND b.millesime = a.millesime + 1
        WHERE a.siren IS DISTINCT FROM b.siren
          AND b.millesime >= :depuis
    )
    SELECT idu, de_m, a_m, s_av, d_av, s_ap, d_ap
    FROM paires ORDER BY a_m DESC, idu LIMIT :lim
    """)
    count_sql = text("""
    WITH unifie AS (
        SELECT millesime, idu, siren FROM pm_proprietaires_millesimes WHERE left(idu, 5) = :insee
        UNION ALL
        SELECT :servi, idu, siren FROM parcelle_personne_morale
        WHERE left(idu, 5) = :insee
          AND NOT EXISTS (SELECT 1 FROM pm_proprietaires_millesimes WHERE millesime = :servi)
    )
    SELECT count(*) FROM unifie a JOIN unifie b
      ON b.idu = a.idu AND b.millesime = a.millesime + 1
    WHERE a.siren IS DISTINCT FROM b.siren AND b.millesime >= :depuis
    """)
    n_total = db.execute(count_sql, {"insee": commune_insee, "servi": _MILLESIME_SERVI,
                                     "depuis": depuis_millesime}).scalar() or 0
    rows = db.execute(sql, {"insee": commune_insee, "servi": _MILLESIME_SERVI,
                            "depuis": depuis_millesime, "lim": limit}).mappings().all()
    items = [{
        "idu": r["idu"],
        "de_millesime": r["de_m"], "a_millesime": r["a_m"],
        "siren_avant": r["s_av"], "denomination_avant": r["d_av"],
        "siren_apres": r["s_ap"], "denomination_apres": r["d_ap"],
    } for r in rows]
    return {
        "source": SOURCE,
        "commune_insee": commune_insee,
        "depuis_millesime": depuis_millesime,
        "n": len(items),
        "n_total": n_total,
        "tronquee": n_total > len(items),
        "acquisitions": items,
        "note": "Constat DGFiP (changement de propriétaire moral d'un millésime au suivant). "
                "N'affirme pas une vente ; hors scoring.",
    }
