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


def siren_reel(siren: str | None) -> bool:
    """DONNEES-FIX-1 lot B — un VRAI SIREN DGFiP = 9 chiffres. Le pseudo-siren « U… » (attribué par
    LABUSE quand la DGFiP n'a pas résolu le SIREN, ~13 % des lignes) et le SIREN absent NE SONT PAS
    des identités juridiques comparables : on ne les fait jamais entrer dans un changement affirmé."""
    s = (siren or "").strip().upper()
    return bool(s) and not s.startswith("U")


def changements_millesimes(rows: list[dict]) -> list[dict]:
    """DONNEES-FIX-1 lot B — RÈGLE UNIQUE des changements de propriétaire PM, lue par la fiche
    §Identité ET la frise « Remonter le temps » (une seule règle, pas une copie E3).

    Un changement n'est AFFIRMÉ (`non_identifiable=False`) que si les deux SIREN sont réels (9
    chiffres, ni pseudo « U… » ni absent) ET différents. Toute autre transition apparente (un SIREN
    pseudo/absent d'un côté, ou dénomination changée sans SIREN réel) est marquée
    `non_identifiable=True` — « propriétaire PM non identifiable » —, jamais un changement inventé
    (cf. audit : SCI Laurent Grandpre, ONF). Une re-clé de dénomination à SIREN réel INCHANGÉ n'est
    pas un changement. `rows` = millésimes triés croissants (clés millesime/siren/denomination)."""
    out: list[dict] = []
    for prev, cur in zip(rows, rows[1:]):
        sa, sb = prev.get("siren"), cur.get("siren")
        da, db_ = prev.get("denomination"), cur.get("denomination")
        base = {
            "de_millesime": prev["millesime"], "a_millesime": cur["millesime"],
            "siren_avant": sa, "denomination_avant": da,
            "siren_apres": sb, "denomination_apres": db_,
        }
        if siren_reel(sa) and siren_reel(sb):
            if sa != sb:                       # deux identités réelles distinctes → VRAI changement
                out.append({**base, "non_identifiable": False})
            continue                           # même SIREN réel → même personne (re-clé de dénom ≠ chgt)
        # au moins un SIREN non réel : on ne peut PAS affirmer. Transition APPARENTE (le brut diffère,
        # côté SIREN OU côté dénomination) → « non identifiable », jamais un changement.
        if ((sa or "") != (sb or "")) or ((da or "") != (db_ or "")):
            out.append({**base, "non_identifiable": True})
    return out


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

    # DONNEES-FIX-1 lot B — changements via la RÈGLE UNIQUE partagée avec la frise : un changement
    # n'est affirmé que si les deux SIREN sont réels et différents ; sinon « non identifiable ». Plus
    # de faux « changements » dus au pseudo-siren « U… » ou au SIREN absent des premiers millésimes.
    changements = changements_millesimes(rows)
    n_reels = sum(1 for c in changements if not c["non_identifiable"])

    return {
        "source": SOURCE,
        "millesimes": millesimes,
        "n_millesimes": len(millesimes),
        "changements": changements,
        # n_changements = changements RÉELS (SIREN réels et différents), pas les transitions « non
        # identifiables ». n_transitions = tout ce qui est listé (réels + non identifiables).
        "n_changements": n_reels,
        "n_transitions": len(changements),
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
