"""Indice de confiance données (ICD) par parcelle — M9 lot 1.

Implémente la SPEC §1.4 A.4 de l'audit M6 (`reports/m6-audit/sections/1-4-scoring-v2.md`).

L'ICD ∈ [0, 100] mesure la **complétude PONDÉRÉE** des groupes de données qui
alimentent le scoring v2 pour une parcelle. C'est une **méta d'affichage** :

  ⚠ CLOISONNEMENT STRICT DU SCORE P ⚠
  L'ICD ne modifie JAMAIS le score P (p_raw), le rang, le percentile ni le tier.
  Le modèle P est GELÉ (sha256 au manifeste) et n'est pas touché. L'ICD est une
  colonne annexe (`parcel_p_score_v2.icd` / `.icd_detail`) calculée EN LECTURE à
  partir de `p_model_ext_dataset` ; aucun ré-entraînement, aucune ré-évaluation.
  Une parcelle à données lacunaires (ICD bas) peut avoir n'importe quel tier :
  l'ICD dit « à quel point les données sont complètes », pas « à quel point c'est
  une opportunité ». Les deux axes sont indépendants par construction.

Ne pas confondre avec `scoring/completeness.py` (score §7A des FAMILLES de la
cascade, autre grain, autre usage) : seul le pattern poids/bandes est réutilisé.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IcdGroup:
    key: str          # identifiant stable (clé de icd_detail)
    label: str        # libellé client (affiché quand le groupe MANQUE)
    poids: int        # contribution à l'ICD quand le groupe est renseigné
    sql_test: str     # expression booléenne SQL sur p_model_ext_dataset (alias `d`)


# Les 9 groupes nullables de A.3, pondérés par l'enjeu (IV de l'artifact + rôle
# dans le plancher C et contrib_D). Total des poids = 100 (invariant testé).
ICD_GROUPS: list[IcdGroup] = [
    IcdGroup("residuel", "capacité PLU non calculée", 20,
             "d.pct_potentiel IS NOT NULL"),
    IcdGroup("zone_plu", "zonage PLU inconnu", 15,
             "d.zone_plu IS NOT NULL AND d.zone_plu <> 'inconnu'"),
    IcdGroup("vegetation", "végétation / canopée non mesurée", 15,
             "d.canopee_pct IS NOT NULL"),
    IcdGroup("prix_terrain", "prix du terrain du secteur inconnus", 10,
             "d.med_pm2_terrain_36m IS NOT NULL"),
    IcdGroup("prix_bati", "prix du bâti du secteur inconnus", 10,
             "d.med_pm2_bati_36m IS NOT NULL"),
    IcdGroup("filosofi", "données socio-démographiques (INSEE) absentes", 10,
             "d.filo_snv_pp IS NOT NULL"),
    IcdGroup("tenure", "historique de propriété inconnu", 10,
             "d.tenure_bin IS NOT NULL AND d.tenure_bin <> 'inconnu'"),
    IcdGroup("tendance_prix", "tendance des prix du secteur inconnue", 5,
             "d.tendance_pm2_bati IS NOT NULL"),
    IcdGroup("pente", "pente du terrain non mesurée", 5,
             "d.pente_moy_deg IS NOT NULL"),
]

POIDS_TOTAL = sum(g.poids for g in ICD_GROUPS)  # == 100
assert POIDS_TOTAL == 100, f"ICD: somme des poids = {POIDS_TOTAL}, doit valoir 100"

# Bandes d'affichage (calées sur la distribution observée : médiane 8/9, P10 ≈ 7/9).
BANDE_HAUTE = 85   # ICD >= 85 : confiance haute, aucun badge (cas nominal)
BANDE_FAIBLE = 60  # ICD < 60 : confiance faible (badge orange + avertissement)


def bande(icd: int | None) -> str:
    """Libellé de bande à partir de l'ICD. Utilisé côté API et exports."""
    if icd is None:
        return "inconnu"
    if icd >= BANDE_HAUTE:
        return "haute"
    if icd >= BANDE_FAIBLE:
        return "partielle"
    return "faible"


def libelle_bande(icd: int | None) -> str:
    """Libellé client de la bande (pour badge/tooltip)."""
    return {
        "haute": "confiance haute",
        "partielle": "données partielles",
        "faible": "confiance faible",
        "inconnu": "confiance non évaluée",
    }[bande(icd)]


def manquants(icd_detail: dict | None) -> list[str]:
    """Libellés client des groupes MANQUANTS, du plus lourd au plus léger."""
    if not icd_detail:
        return []
    out = []
    for g in ICD_GROUPS:
        present = icd_detail.get(g.key)
        if present is False:  # explicitement absent (None = groupe non évalué)
            out.append(g.label)
    return out


def compute_from_row(row: dict) -> tuple[int, dict]:
    """Calcule (icd, icd_detail) depuis une ligne `p_model_ext_dataset`.

    `row` : dict avec au moins les colonnes testées. Sert de référence Python
    (tests d'invariance, calcul à la volée). La vérité SQL est `backfill_run`."""
    detail: dict[str, bool] = {}
    total = 0
    for g in ICD_GROUPS:
        present = _eval_group(g.key, row)
        detail[g.key] = present
        if present:
            total += g.poids
    return total, detail


def _eval_group(key: str, row: dict) -> bool:
    g = {x.key: x for x in ICD_GROUPS}[key]
    v = lambda c: row.get(c)  # noqa: E731
    if key == "residuel":
        return v("pct_potentiel") is not None
    if key == "zone_plu":
        return v("zone_plu") not in (None, "inconnu")
    if key == "vegetation":
        return v("canopee_pct") is not None
    if key == "prix_terrain":
        return v("med_pm2_terrain_36m") is not None
    if key == "prix_bati":
        return v("med_pm2_bati_36m") is not None
    if key == "filosofi":
        return v("filo_snv_pp") is not None
    if key == "tenure":
        return v("tenure_bin") not in (None, "inconnu")
    if key == "tendance_prix":
        return v("tendance_pm2_bati") is not None
    if key == "pente":
        return v("pente_moy_deg") is not None
    raise KeyError(g.key)


def _update_sql() -> str:
    """UPDATE qui écrit icd + icd_detail pour toutes les lignes d'un run.

    Construit dynamiquement depuis ICD_GROUPS (aucune divergence SQL/Python).
    Lit `p_model_ext_dataset` (année = :annee) ; n'écrit QUE icd/icd_detail."""
    icd_expr = " + ".join(
        f"(CASE WHEN {g.sql_test} THEN {g.poids} ELSE 0 END)" for g in ICD_GROUPS
    )
    detail_pairs = ", ".join(
        f"'{g.key}', ({g.sql_test})" for g in ICD_GROUPS
    )
    return f"""
        UPDATE parcel_p_score_v2 s
           SET icd = ({icd_expr})::smallint,
               icd_detail = jsonb_build_object({detail_pairs})
          FROM p_model_ext_dataset d
         WHERE d.idu = s.parcelle_id
           AND d.annee = :annee
           AND s.run_id = :run
    """


def backfill_run(session, run_id: str, annee: int | None = None) -> int:
    """Backfill LECTURE des colonnes icd/icd_detail pour un run existant.

    Aucun recalcul de modèle : lit `p_model_ext_dataset` et écrit deux colonnes
    annexes. Retourne le nombre de lignes mises à jour."""
    from sqlalchemy import text

    if annee is None:
        annee = session.execute(
            text("SELECT max(annee) FROM p_model_ext_dataset")
        ).scalar()
    res = session.execute(text(_update_sql()), {"run": run_id, "annee": annee})
    return res.rowcount or 0
