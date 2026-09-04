"""O6 — COMPARATEUR DE COMMUNES : « où investir ? » un tableau, une ligne par commune.

Agrège des indicateurs DÉJÀ en base (zéro donnée nouvelle), un par colonne, chacun Sourcé/Estimé :
  · stock d'opportunités (parcelles brûlantes + chaudes du run servi) ;
  · vélocité administrative (délai médian dépôt→autorisation des permis logements, m10) ;
  · dynamisme permis (SITADEL, 24 derniers mois) ;
  · déficit SRU (écart objectif − taux LLS, DHUP) ;
  · pression ZAN (ENAF consommé 2021-2024, Cerema) ;
  · prix de sortie neuf (DVF, niveau commune).

Le classement composite est une **commodité, pas un score calibré** : la pondération est **présentée,
réglable** (query params) et **documentée** ; chaque indicateur est normalisé min-max [0-100] avec sa
direction (plus haut = « mieux pour investir »). Tout est labellisé ; une commune sans donnée sur un axe
reste `null` (jamais 0 trompeur) et l'axe est ignoré dans SON composite (renormalisation des poids présents).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import runs
# communes-tableau — le « €/m² ancien » vient de la MÊME source que le Baromètre (DVF ventes strictes,
# toutes mutations) : on réutilise le filtre de retenue du baromètre, point de vérité unique.
from .moteurs import prix_ancien_communes

log = logging.getLogger("labuse.comparateur")
router = APIRouter(prefix="/comparateur-communes", tags=["comparateur-communes"])

# Indicateur → (libellé, direction, poids par défaut, source, nature).
# direction +1 = plus haut « mieux pour investir » ; -1 = plus bas mieux (on inverse à la normalisation).
# NB communes-tableau : `prix_ancien` est une COLONNE d'affichage (pas un axe composite) — hors INDICATEURS.
INDICATEURS = {
    "stock":     ("Stock d'opportunités (brûlantes + chaudes)", +1, 0.30, "run servi", "Sourcé"),
    "velocite":  ("Vélocité admin (délai médian dépôt→autorisation, mois)", -1, 0.15, "m10 / SITADEL", "Sourcé"),
    "permis":    ("Dynamisme permis (SITADEL, 5 ans)", +1, 0.15, "SITADEL", "Sourcé"),
    "deficit_sru": ("Déficit SRU (objectif − taux LLS, points)", +1, 0.15, "DHUP", "Sourcé"),
    "pression_zan": ("Pression ZAN (ENAF consommé 2021-2024, ha)", -1, 0.10, "Cerema", "Sourcé"),
    "prix_neuf": ("Prix de sortie neuf VEFA (DVF, €/m²)", +1, 0.15, "DVF", "Sourcé"),
}

_SQL = f"""
WITH base AS (SELECT DISTINCT left(idu, 5) AS insee, commune FROM parcels),
stock AS (
  SELECT left(s.parcelle_id, 5) AS insee,
         count(*) FILTER (WHERE s.tier IN ('brulante', 'chaude')) AS n
  FROM parcel_p_score_v2 s WHERE s.run_id = :run GROUP BY 1),
velo AS (
  SELECT commune, percentile_cont(0.5) WITHIN GROUP (ORDER BY delai_mois) AS mois, count(*) AS n
  FROM m10_permit_delais WHERE valide AND famille = 'logements' AND delai_mois >= 0 GROUP BY 1),
permis AS (
  SELECT commune, count(*) AS n FROM sitadel_permits
  WHERE date >= (CURRENT_DATE - INTERVAL '5 years') GROUP BY 1),
sru AS (SELECT insee, greatest(objectif_pct - taux_lls, 0) AS deficit, statut FROM commune_contexte_sru),
zan AS (SELECT insee, conso_2021_2024_m2 / 10000.0 AS ha FROM commune_conso_enaf)
-- €/m² ANCIEN : SOURCE UNIQUE `prix_ancien_communes` (moteurs), mappée en Python (cf. _compute) —
-- plus de CTE recopiée : le tableau Communes et le PDF baromètre lisent la MÊME fonction (§1b).
-- RETOURS-11F M1 : le NEUF (prix_neuf) ne vient PLUS de `dvf_prix_sortie_neuf` (précalcul divergent —
-- mesuré Saint-Paul 97415 : précalc 4 730 vs live 5 003) mais du MÊME moteur live `neuf_vefa_commune`
-- que la fiche et la carte, calculé en Python dans `raw_rows` (fiche = table = carte, à l'euro près).
SELECT b.insee, b.commune,
       stock.n AS stock, velo.mois AS velocite, velo.n AS velocite_n, permis.n AS permis,
       sru.deficit AS deficit_sru, sru.statut AS sru_statut,
       zan.ha AS pression_zan
FROM base b
LEFT JOIN stock ON stock.insee = b.insee
LEFT JOIN velo ON velo.commune = b.commune
LEFT JOIN permis ON permis.commune = b.commune
LEFT JOIN sru ON sru.insee = b.insee
LEFT JOIN zan ON zan.insee = b.insee
ORDER BY b.commune;
"""


def get_db():
    from .app import get_db as _g
    yield from _g()


def _normalize(rows: list[dict], poids: dict) -> list[dict]:
    """Normalise chaque indicateur min-max [0-100] selon sa direction ; composite = moyenne pondérée
    des axes PRÉSENTS (renormalisation des poids présents pour ne pas pénaliser une donnée manquante)."""
    keys = list(INDICATEURS)
    bornes = {}
    for k in keys:
        vals = [r[k] for r in rows if r.get(k) is not None]
        bornes[k] = (min(vals), max(vals)) if vals else (None, None)
    for r in rows:
        norm, wsum, wtot = {}, 0.0, 0.0
        for k in keys:
            direction = INDICATEURS[k][1]
            lo, hi = bornes[k]
            v = r.get(k)
            if v is None or lo is None or hi == lo:
                norm[k] = None if v is None else 50.0   # borne dégénérée → neutre
            else:
                frac = (v - lo) / (hi - lo)
                norm[k] = round((frac if direction > 0 else 1 - frac) * 100, 1)
            w = poids.get(k, 0.0)
            wtot += w
            if norm[k] is not None:
                wsum += w * norm[k]
                # cumul du poids réellement appliqué (axes présents)
        present_w = sum(poids.get(k, 0.0) for k in keys if norm[k] is not None)
        r["normalise"] = norm
        r["score_composite"] = round(wsum / present_w, 1) if present_w > 0 else None
    rows.sort(key=lambda r: (r["score_composite"] is not None, r["score_composite"] or 0), reverse=True)
    for i, r in enumerate(rows, 1):
        r["rang"] = i
    return rows


def raw_rows(db: Session) -> dict[str, dict]:
    """SOURCE UNIQUE des indicateurs bruts PAR COMMUNE (avant normalisation) — le comparateur ET la
    fiche commune (OUTILS-6 C2) la lisent : ancien/neuf/permis/vélocité/stock viennent du MÊME run et
    des MÊMES requêtes des deux côtés, donc chaque chiffre commun est identique. Mémoïsé (crons
    quotidiens ; single-flight anti-stampede). Clé = nom de commune."""
    from .app import _mem_cached

    def _c():
        from ..ingestion.dvf_marche import neuf_vefa_commune
        from ..marche_service import neuf_vefa_seuil
        from ..faisabilite.marche_commune import ligne2_terrain_zone
        seuil = neuf_vefa_seuil()
        rows = [dict(r) for r in db.execute(text(_SQL), {"run": runs.current()}).mappings().all()]
        pa = prix_ancien_communes(db)   # §1b — SOURCE UNIQUE du €/m² ancien (partagée avec le PDF baromètre)
        for r in rows:
            r["prix_ancien"] = (pa.get(r["commune"]) or {}).get("median")
            r["prix_ancien_n"] = (pa.get(r["commune"]) or {}).get("n")
            # RETOURS-11F M1 — NEUF depuis le moteur live (même seuil/fenêtre que la fiche et la carte) :
            # sous le seuil, prix_neuf reste null (jamais un chiffre fragile ni un précalcul périmé).
            v = neuf_vefa_commune(db, r["insee"])
            suffisant = v["n"] >= seuil and v["mediane_prix_m2_bati"] is not None
            r["prix_neuf"] = v["mediane_prix_m2_bati"] if suffisant else None
            r["prix_neuf_n"] = v["n"]
            # RETOURS-11F M13 — €/m² TERRAIN NU DVF (« le chiffre du promoteur », O14) : MÊME moteur
            # que la fiche (Marché) et la calculette — `ligne2_terrain_zone`, aucun calcul parallèle.
            # Zone U de préférence, sinon AU ; sous le seuil de cellule → null (jamais un 0 trompeur).
            try:
                pz = (ligne2_terrain_zone(db, r["commune"]).get("valeurs") or {}).get("par_zone") or {}
            except Exception:  # noqa: BLE001 — le terrain nu ne casse jamais le tableau
                pz = {}
            tn = None
            for fam in ("U", "AU"):
                cell = pz.get(fam) or {}
                if cell.get("calculable") and cell.get("median_eur_m2"):
                    tn = {"eur_m2": cell["median_eur_m2"], "n": cell.get("n"), "zone": fam}
                    break
            r["prix_terrain_nu"] = tn["eur_m2"] if tn else None
            r["prix_terrain_nu_n"] = tn["n"] if tn else None
            r["prix_terrain_nu_zone"] = tn["zone"] if tn else None
        return {r["commune"]: r for r in rows}
    return _mem_cached(("o6-raw",), 3600.0, _c)


def _compute(db: Session, poids: dict) -> dict:
    """Cœur testable : assemble les indicateurs par commune, normalise, compose. `poids` = dict d'axes→poids."""
    rows = [dict(r) for r in raw_rows(db).values()]
    for r in rows:   # arrondis lisibles (les valeurs brutes restent la vérité)
        if r.get("velocite") is not None:
            r["velocite"] = round(float(r["velocite"]), 1)
        if r.get("pression_zan") is not None:
            r["pression_zan"] = round(float(r["pression_zan"]), 1)
        if r.get("deficit_sru") is not None:
            r["deficit_sru"] = round(float(r["deficit_sru"]), 1)
    rows = _normalize(rows, poids)
    return {
        "communes": rows,
        "indicateurs": {k: {"libelle": v[0], "direction": "haut = mieux" if v[1] > 0 else "bas = mieux",
                            "poids": poids.get(k), "source": v[3], "nature": v[4]}
                        for k, v in INDICATEURS.items()},
        "poids_total": round(sum(poids.values()), 3),
        "methode": ("Composite de COMMODITÉ (non calibré) : chaque indicateur normalisé min-max [0-100] selon sa "
                    "direction, moyenne pondérée des axes présents (poids renormalisés si une donnée manque). "
                    "La pondération est réglable via les paramètres w_* ; les valeurs brutes restent la référence."),
        "avertissement": "Aide à la comparaison, pas un score de rendement ; un axe manquant reste null (jamais 0).",
    }


@router.get("")
def comparateur_communes(
    db: Session = Depends(get_db),
    w_stock: float = Query(0.30, ge=0, le=1), w_velocite: float = Query(0.15, ge=0, le=1),
    w_permis: float = Query(0.15, ge=0, le=1), w_deficit_sru: float = Query(0.15, ge=0, le=1),
    w_pression_zan: float = Query(0.10, ge=0, le=1), w_prix_neuf: float = Query(0.15, ge=0, le=1),
) -> dict:
    """Tableau « où investir » : une ligne par commune, indicateurs sourcés + composite à pondération réglable."""
    poids = {"stock": w_stock, "velocite": w_velocite, "permis": w_permis,
             "deficit_sru": w_deficit_sru, "pression_zan": w_pression_zan, "prix_neuf": w_prix_neuf}
    # BLOC B (B1.4) : cache TTL 1 h par jeu de pondérations (mêmes raisons/rythme que le
    # carnet O7 : les indicateurs suivent les crons quotidiens ; single-flight anti-stampede).
    from .app import _mem_cached
    return _mem_cached(("o6", tuple(sorted(poids.items()))), 3600.0, lambda: _compute(db, poids))
