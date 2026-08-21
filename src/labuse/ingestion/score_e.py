"""NUIT 2026-07-21, lot N1 — SCORE É v1 : la marge cachée en euros.

Le classement que le client comprend sans explication : combien cette parcelle peut rapporter.

  marge_estimee = charge_fonciere_supportable − prix_probable_foncier

Table ADDITIVE `score_e`. Ne touche JAMAIS les tables servies. Univers : parcelles NON-ÉCARTÉES de
run SERVI (Q_A_RUN_LABEL). Tout est **Estimé** — jamais un prix ni une promesse ; jamais de marge sur une écartée.
M44 Lot 0 : le défaut d'argument était `q_v7_defisc` (run mort) — aligné sur le point de vérité (served_run.txt).

O0 (V2) — le prix de sortie n'est plus la médiane DVF de l'EXISTANT (~2 265 €/m², ancien dilué qui
écrasait 90 % des marges) mais le **prix de sortie NEUF** reconstruit par `dvf_prix_sortie_neuf`
(ventes ≤ 3 ans après achèvement d'un PC ; ~3 688 €/m² médian), avec repli secteur→commune→non estimable.
Un promoteur vend du neuf : c'est le prix économiquement juste pour une charge foncière de promotion.

Méthode (batch, hypothèses par DÉFAUT du bilan — cf. `faisabilite/bilan.py`) :
- **charge supportable** = bilan à REBOURS, version batch : `CA×coef − construction`, où
    CA = surf_habitable × prix_sortie_NEUF_secteur ; surf_habitable = SDP_résiduelle / coef_plancher (1,15) ;
    coef = 1 − (marge 9 % + frais 12 %) = 0,79 ; construction = SDP_résiduelle × milieu de la
    fourchette auditée du YAML (2300-2800 → 2 550 €/m² — DÉRIVÉ de la source unique, plus de constante).
    (VRD = 0 : paramètre sectoriel non calibré en batch — hypothèse prudente, documentée.)
    Prix de sortie = médiane NEUF `dvf_prix_sortie_neuf` au niveau secteur (préfixe IDU 10) si n ≥ 5,
    sinon repli commune (INSEE 5) si n ≥ 5 — le niveau retenu est tracé (`niveau_prix`).
- **prix probable** = `dvf_secteur_medianes[terrain].mediane_prix_m2 × surface_m2`.
- **marge** = charge − prix probable. Peut être NÉGATIVE (affichée comme telle).

Non estimable (pas de chiffre inventé) si : pas de SDP résiduelle, OU prix de vente sectoriel absent/trop
peu de ventes, OU prix terrain sectoriel absent. On stocke alors `estimable=false`, marge NULL.

CAVEATS (Estimé) : médiane sectorielle ≠ prix négocié ; hypothèses de bilan génériques ; hors coûts
spécifiques (démolition, dépollution, VRD, stationnement, TVA, aléas).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..scoring.score_v_constants import Q_A_RUN_LABEL  # M44 Lot 0 : point de vérité (served_run.txt)

# Hypothèses DÉRIVÉES de la source unique (`hypotheses_faisabilite` YAML — mandat hypothèses
# bilan, décision Vic 28/07/2026) : plus de constante de coût autonome ici. Numériquement
# identiques à « bilan-neuf-v2 » tant que le YAML porte l'audit O2 (2300-2800 → milieu 2550,
# coef plancher 1,15, coef CA 0,79) ; la version tracée expose les valeurs effectives.
def _hyp_source_unique() -> tuple[float, float, float]:
    from ..faisabilite.engine import Hypotheses
    h = Hypotheses.charger()
    cout = round((h.cout_construction_m2_bas + h.cout_construction_m2_haut) / 2)
    coef_ca = round(1.0 - (h.marge_promoteur_pct + h.frais_annexes_pct), 4)
    return float(h.coef_plancher_habitable), coef_ca, float(cout)


COEF_PLANCHER, COEF_CA, COUT_M2 = _hyp_source_unique()
HYP_VERSION = (f"bilan-neuf-v2 · source-unique constr. {COUT_M2:.0f} €/m² · "
               f"coef_plancher {COEF_PLANCHER:g} · coef CA {COEF_CA:g} · VRD 0")
N_MIN_VENTE = 5                        # ventes min pour un prix de sortie sectoriel (CA)
N_MIN_TERRAIN = 3                      # ventes min pour un prix terrain sectoriel

DDL = """
CREATE TABLE IF NOT EXISTS score_e (
  idu                varchar(14) PRIMARY KEY REFERENCES parcels (idu),
  estimable          boolean NOT NULL,
  marge_estimee      int,               -- € (peut être négatif) — NULL si non estimable
  charge_supportable int,               -- € (bilan à rebours, Estimé)
  prix_probable      int,               -- € (médiane terrain sectorielle × surface, Estimé)
  niveau_prix        text,               -- 'secteur' | 'commune' : niveau du prix de sortie neuf retenu (NULL si non estimable)
  hypotheses_version text NOT NULL,
  libelle_court      text NOT NULL,     -- chip fiche
  detail             text NOT NULL,     -- survol : formule + caveats
  run_label          text,               -- M50 : run servi dont sont issus les tiers/résiduels lus
  computed_at        timestamptz DEFAULT now()
);
"""

# non-écartées q_v7_defisc + SDP résiduelle + prix terrain sectoriel + prix de sortie NEUF (secteur→commune)
_SELECT_RAW = """
WITH med AS (
  SELECT secteur,
         max(mediane_prix_m2) FILTER (WHERE type_bien='terrain' AND n_ventes >= :nt) AS terrain
  FROM dvf_secteur_medianes GROUP BY secteur),
neuf_sec AS (SELECT cle, prix_m2_neuf FROM dvf_prix_sortie_neuf WHERE niveau='secteur'),
neuf_com AS (SELECT cle, prix_m2_neuf FROM dvf_prix_sortie_neuf WHERE niveau='commune'),
-- MANDAT COUVERTURE PRIX (Vic 28/07/2026) — REPLI ÎLE : médiane marché île (non indexée), servie
-- aux communes de MARCHÉ sans prix local ; les communes social-dominantes n'y accèdent pas.
neuf_ile AS (SELECT prix_m2_neuf FROM dvf_prix_sortie_neuf WHERE niveau='ile' LIMIT 1)
SELECT p.idu,
       p.surface_m2,
       r.sdp_residuelle_m2 AS sdp,
       m.terrain,
       COALESCE(ns.prix_m2_neuf, nc.prix_m2_neuf,
                CASE WHEN left(p.idu,5) <> ALL(:social) THEN (SELECT prix_m2_neuf FROM neuf_ile) END) AS prix_vente,
       CASE WHEN ns.prix_m2_neuf IS NOT NULL THEN 'secteur'
            WHEN nc.prix_m2_neuf IS NOT NULL THEN 'commune'
            WHEN left(p.idu,5) <> ALL(:social) AND (SELECT prix_m2_neuf FROM neuf_ile) IS NOT NULL
                 THEN CASE WHEN left(p.idu,5) = ANY(:validees) THEN 'ile_validee' ELSE 'ile_sans_operation' END
            END AS niveau_prix
FROM parcel_p_score_v2 s
JOIN parcels p ON p.idu = s.parcelle_id
LEFT JOIN parcel_residuel r ON r.parcel_id = p.id AND r.cause IS NULL
LEFT JOIN med m ON m.secteur = left(p.idu, 10)
LEFT JOIN neuf_sec ns ON ns.cle = left(p.idu, 10)
LEFT JOIN neuf_com nc ON nc.cle = left(p.idu, 5)
WHERE s.run_id = :run AND s.tier <> 'ecartee';
"""

_INSERT = """
INSERT INTO score_e (idu, estimable, marge_estimee, charge_supportable, prix_probable,
                     niveau_prix, hypotheses_version, libelle_court, detail, run_label, computed_at)
VALUES (:idu, :estimable, :marge, :charge, :prix, :niveau, :hv, :court, :detail, :run_label, now())
ON CONFLICT (idu) DO UPDATE SET
  estimable = EXCLUDED.estimable, marge_estimee = EXCLUDED.marge_estimee,
  charge_supportable = EXCLUDED.charge_supportable, prix_probable = EXCLUDED.prix_probable,
  niveau_prix = EXCLUDED.niveau_prix, hypotheses_version = EXCLUDED.hypotheses_version,
  libelle_court = EXCLUDED.libelle_court, detail = EXCLUDED.detail,
  run_label = EXCLUDED.run_label, computed_at = now();
"""

_CAVEAT = ("Estimé (hypothèses de bilan génériques) — prix de sortie neuf médian DVF ≠ prix négocié ; "
           "hors coûts spécifiques (démolition, dépollution, VRD, stationnement, TVA, aléas). "
           "N'est ni un prix ni une promesse.")


def niveau_label(niveau_prix: str | None) -> str:
    """Libellé CLIENT du niveau du prix de sortie neuf (exigence Vic : niveau_prix visible).
    Tooltip/détail fiche + dossier banquier s'appuient dessus. Repli île = mandat couverture prix."""
    return {"secteur": "estimation niveau secteur",
            "commune": "estimation niveau commune",
            "ile_validee": "estimation à l'échelle de l'île (± 12 %)",
            "ile_sans_operation": "estimation île, aucune opération de marché observée sur cette commune",
            }.get(niveau_prix, "estimation niveau non déterminé")


def _eur(x: int) -> str:
    ax = abs(x)
    if ax >= 1_000_000:
        return f"{x / 1_000_000:.1f} M€"
    if ax >= 1_000:
        return f"{x / 1_000:.0f} k€"
    return f"{x:.0f} €"


def _row(idu, surface_m2, sdp, terrain, prix_vente, niveau_prix) -> dict:
    if not sdp or sdp <= 0 or not terrain or not prix_vente or not surface_m2:
        court = "Marge estimée : non estimable"
        detail = ("Marge non estimable : données de marché sectorielles insuffisantes "
                  "(prix de sortie neuf, prix terrain, ou surface constructible manquants). Pas de chiffre inventé.")
        return {"idu": idu, "estimable": False, "marge": None, "charge": None, "prix": None,
                "niveau": None, "hv": HYP_VERSION, "court": court, "detail": detail}
    surf_habitable = sdp / COEF_PLANCHER
    charge = round(surf_habitable * prix_vente * COEF_CA - sdp * COUT_M2)
    prix = round(terrain * surface_m2)
    marge = charge - prix
    signe = "+" if marge >= 0 else "−"
    niveau_txt = niveau_label(niveau_prix)   # « estimation niveau secteur » / « … commune (repli) »
    court = f"Marge estimée : {signe}{_eur(abs(marge))} · Estimé"
    detail = (
        f"Marge estimée {_eur(marge)} = charge foncière supportable {_eur(charge)} − prix probable du "
        f"foncier {_eur(prix)}. Charge = bilan à rebours (prix de sortie neuf {prix_vente:.0f} €/m², {niveau_txt} "
        f"× {COEF_CA:g} − construction {COUT_M2:.0f} €/m²) ; prix probable = médiane terrain sectorielle × {surface_m2:.0f} m². {_CAVEAT}")
    return {"idu": idu, "estimable": True, "marge": marge, "charge": charge, "prix": prix,
            "niveau": niveau_prix, "hv": HYP_VERSION, "court": court, "detail": detail}


def build_score_e(session: Session, *, run: str = Q_A_RUN_LABEL,
                  commit: bool = True, log=lambda *_: None) -> dict:
    """Construit/rafraîchit `score_e` (rebuild complet idempotent). Lecture seule des sources.
    `commit=False` pour les tests transactionnels. Renvoie {'total', 'estimables'}."""
    from .dvf_prix_neuf import SOCIAL_DOMINANT_INSEE, ILE_VALIDEES_INSEE
    # M-O P2-59 — rebuild NON BLOQUANT (table lue en direct par division_or + scoreur d'adresse ;
    # ~13 s de build). SELECT + INSERT hors-ligne dans une shadow, swap ~ms (cf. _rebuild).
    from ._rebuild import rebuild_swap

    def _populate(target: str) -> dict:
        raw = session.execute(text(_SELECT_RAW),
                              {"run": run, "nt": N_MIN_TERRAIN, "nv": N_MIN_VENTE,
                               "social": list(SOCIAL_DOMINANT_INSEE),
                               "validees": list(ILE_VALIDEES_INSEE)}).mappings().all()
        rows = [_row(r["idu"], r["surface_m2"], r["sdp"], r["terrain"], r["prix_vente"], r["niveau_prix"]) for r in raw]
        ins = text(_INSERT.replace("INTO score_e", f'INTO "{target}"', 1))
        for r in rows:
            session.execute(ins, {**r, "run_label": run})        # M50 : stamp du run servi lu
        return {"total": len(rows), "estimables": sum(1 for r in rows if r["estimable"])}

    out = rebuild_swap(session, "score_e", DDL, _populate, commit=commit)
    log(f"score_e : {out['total']} parcelles non-écartées, {out['estimables']} avec marge estimable")
    return out
