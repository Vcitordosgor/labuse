"""PPR-UNIQUE-1 (décision Vic 31/10/2026) — LECTURE UNIQUE des Plans de Prévention des Risques.

Un seul module de lecture des zones PPR (`spatial_layers.kind='ppr'`), utilisé par la fiche,
l'Étude de faisabilité, le Gabarit, Pièges et risques et tous les PDF. Avant ce module, quatre
classificateurs divergeaient (sous-chaîne « interdict »/« rouge », `subtype='INTERDICTION'`,
`IN ('interdiction','i')`, config `ppr_red_subtypes`) : seul l'un d'eux reconnaissait le code
hérité `i` de Saint-Philippe, d'où l'Étude dessinant 42 logements sur une parcelle 100 % rouge
(audit NU-D-001, 1 237 parcelles).

Doctrine PPR-PARTIEL (Vic) : **seule la PART en zone rouge est interdite** ; le reste suit les
règles de sa zone. On ne déclare jamais « rouge = toute la parcelle inconstructible ».

Classification (miroir EXACT de la fonction SQL `labuse_ppr_couleur`, cf. `models.PPR_COULEUR_FN`) :
  - `rouge` : zone d'INTERDICTION (inconstructible — C. env. L562-1, quelle que soit la surface) ;
  - `bleu`  : zone de PRESCRIPTION (constructible SOUS conditions du règlement DEAL) ;
  - `autre` : code non classé → **traité en rouge par prudence** et **journalisé**, jamais ignoré
              (on ne dessine jamais dans une zone PPR dont la couleur n'est pas certaine).

La « partie interdite » à retrancher de l'assiette constructible = rouge ∪ autre, soit en SQL
`labuse_ppr_couleur(subtype, attrs) <> 'bleu'` et en Python `est_interdit(classer(...))`.
"""
from __future__ import annotations

import logging
import re

log = logging.getLogger("labuse.ppr")

#: Les trois classes de couleur d'une zone PPR.
ROUGE, BLEU, AUTRE = "rouge", "bleu", "autre"

#: Couleurs dont la surface est INTERDITE à la construction (retranchée de l'assiette) : le rouge
#: réglementaire ET tout code non classé (prudence). Le bleu reste constructible sous prescriptions.
COULEURS_INTERDITES: tuple[str, str] = (ROUGE, AUTRE)

def couleur_sql(alias: str = "sl") -> str:
    """Fragment SQL unique classant une ligne `spatial_layers` PPR (`<alias>.subtype`, `<alias>.attrs`)
    → 'rouge' | 'bleu' | 'autre'. À interpoler dans les requêtes des moteurs pour qu'elles partagent
    TOUTES la même lecture (fiche, Étude, Gabarit, Pièges, PDF)."""
    return f"labuse_ppr_couleur({alias}.subtype, {alias}.attrs)"


def interdit_sql(alias: str = "sl") -> str:
    """Prédicat SQL « cette zone PPR est INTERDITE (rouge ∪ code non classé) » : `couleur <> 'bleu'`
    (le `<> 'bleu'` embarque 'autre' = traité en rouge par prudence)."""
    return f"{couleur_sql(alias)} <> 'bleu'"


#: Raccourcis pour l'alias par défaut `sl` (compat lecture rapide).
COULEUR_SQL = couleur_sql("sl")
INTERDIT_SQL = interdit_sql("sl")

_RE_ROUGE = re.compile(r"^[rb]?R")   # sensible à la casse : R majuscule = rouge (après variante r/b)
_RE_BLEU = re.compile(r"^[rb]?B")    # B majuscule = bleu

#: codes déjà journalisés (une seule ligne de log par code non classé, pas une par parcelle).
_autres_vus: set[str] = set()


def classer(subtype: str | None, code_degre: str | None = None,
            code_risque: str | None = None) -> str:
    """Couleur normalisée d'une zone PPR → 'rouge' | 'bleu' | 'autre'. Miroir de `labuse_ppr_couleur`.

    Un code tombant en 'autre' (non classé) est journalisé UNE fois (prudence : il sera traité en
    rouge par `est_interdit`). `subtype` fait foi ; repli sur `code_degre` (R…/rR… rouge, B…/rB…
    bleu) ; tout le reste → 'autre'."""
    s = (subtype or "").strip().upper()
    if s == "INTERDICTION":
        return ROUGE
    if s == "PRESCRIPTION":
        return BLEU
    # Repli sur le code de zone DEAL : la COULEUR est la 1ʳᵉ lettre MAJUSCULE (R=rouge, B=bleu),
    # précédée d'un éventuel marqueur de variante en minuscule (r/b), ex. 'rB3' (bleu), 'rR2' (rouge).
    cd = (code_degre or "").strip()
    if _RE_ROUGE.match(cd):
        return ROUGE
    if _RE_BLEU.match(cd):
        return BLEU
    code = subtype or code_degre or code_risque or "∅"
    if code not in _autres_vus:
        _autres_vus.add(code)
        log.warning("PPR : code non classé %r traité en ROUGE par prudence (zone interdite, "
                    "jamais ignorée).", code)
    return AUTRE


def est_interdit(couleur: str) -> bool:
    """Vrai si la surface de cette couleur est inconstructible (rouge réglementaire OU code non classé)."""
    return couleur in COULEURS_INTERDITES


def est_interdit_ligne(subtype: str | None, code_degre: str | None = None,
                       code_risque: str | None = None) -> bool:
    """Raccourci : classe la ligne PPR et dit si sa surface est interdite (à retrancher de l'assiette)."""
    return est_interdit(classer(subtype, code_degre, code_risque))


def lire_zones_interdites_wkt(session, geom_wkt: str):
    """Zones PPR de couleur INTERDITE (rouge ∪ non classé) intersectant l'assiette `geom_wkt` (2975).

    Rend (geom_rouge_union | None, geom_bleue_union | None) en coordonnées 2975, déjà intersectées
    avec l'assiette. Remplace l'ancien `implantation.terrain._ppr_par_couleur` : la classification
    passe par le module (donc par `labuse_ppr_couleur`), si bien que `i`/code non classé est bien
    retranché (NU-D-001). Les géométries invalides sont ignorées silencieusement (une par une) pour
    ne jamais casser le calcul d'une Étude."""
    from shapely import wkt as shp_wkt
    from shapely.ops import unary_union
    from sqlalchemy import text

    rows = session.execute(text(
        "SELECT subtype, attrs->>'code_degre' AS code_degre, attrs->>'code_risque' AS code_risque, "
        "       ST_AsText(ST_Intersection(geom_2975, ST_GeomFromText(:g,2975))) AS wkt "
        "FROM spatial_layers WHERE kind='ppr' "
        "  AND ST_Intersects(geom_2975, ST_GeomFromText(:g,2975))"
    ), {"g": geom_wkt}).fetchall()
    interdites, bleues = [], []
    for sub, cd, cr, w in rows:
        if not w:
            continue
        try:
            g = shp_wkt.loads(w)
        except Exception:  # noqa: BLE001 — WKT dégénéré : zone ignorée, jamais une 500
            continue
        if g.is_empty:
            continue
        (interdites if est_interdit_ligne(sub, cd, cr) else bleues).append(g)
    rouge = unary_union(interdites) if interdites else None
    bleue = unary_union(bleues) if bleues else None
    return rouge, bleue


def inventaire(session) -> list[dict]:
    """Inventaire des codes PPR distincts présents en base, rangés en rouge/bleu/autre (recette
    PPR-UNIQUE-1). Une ligne par (couleur, subtype, code_degre) avec le nombre de zones."""
    from sqlalchemy import text
    rows = session.execute(text(
        f"SELECT {COULEUR_SQL} AS couleur, sl.subtype, sl.attrs->>'code_degre' AS code_degre, "
        "       sl.attrs->>'code_risque' AS code_risque, count(*) AS n "
        "FROM spatial_layers sl WHERE sl.kind='ppr' "
        "GROUP BY 1,2,3,4 ORDER BY 1,2,3"
    )).mappings().all()
    return [dict(r) for r in rows]


def date_approbation_commune(session, insee: str | None) -> str | None:
    """FIX-NU3-3 (L-MIL-01) — la date d'approbation PPR de LA COMMUNE de la parcelle (ISO AAAA-MM-JJ),
    lue dans `spatial_layers kind='ppr_etat'` (une entité par commune, `attrs.code_insee` +
    `ppr_littoral_date` / `ppr_inond_mvt_date`). Un PPR est COMMUNAL : afficher la date globale (la
    plus récente de TOUTES les communes, Saint-André 2026-04-16) sur chaque fiche faussait la
    perception de l'opposabilité (Le Tampon 2017-10-20, Saint-Leu 2015-11-23…). Retourne la plus
    récente des dates PPR de la commune, ou None si la commune n'a pas de PPR daté."""
    if not insee:
        return None
    from sqlalchemy import text
    try:
        rows = session.execute(text(
            "SELECT attrs->>'ppr_littoral_date' AS d1, attrs->>'ppr_inond_mvt_date' AS d2 "
            "FROM spatial_layers WHERE kind='ppr_etat' AND attrs->>'code_insee' = :insee"),
            {"insee": str(insee)[:5]}).mappings().all()
    except Exception:  # noqa: BLE001 — table/colonne absente : pas de date communale, jamais un crash
        return None
    dates = [d for r in rows for d in (r["d1"], r["d2"]) if d and str(d)[:4].isdigit()]
    return max(dates) if dates else None


def libelle_millesime_commune(session, insee: str | None) -> str | None:
    """FIX-NU3-3 (L-MIL-01) — le libellé PPR daté PAR COMMUNE pour « Les données » / la cascade :
    « PPR approuvé le JJ/MM/AAAA (commune) » si la commune a un PPR daté ; « pas de PPR approuvé sur
    la commune » sinon (jamais la date d'une AUTRE commune). None → l'appelant garde le libellé global."""
    d = date_approbation_commune(session, insee)
    if d:
        return f"PPR approuvé le {d[8:10]}/{d[5:7]}/{d[0:4]} (commune)"
    return None


def codes_non_classes(session) -> list[str]:
    """Liste (journalisable) des subtypes/codes PPR tombant en 'autre' (traités en rouge par prudence)."""
    inv = inventaire(session)
    vus: list[str] = []
    for r in inv:
        if r["couleur"] == AUTRE:
            code = r["subtype"] or r["code_degre"] or r["code_risque"] or "∅"
            if code not in vus:
                vus.append(code)
    return vus
