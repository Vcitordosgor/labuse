"""NUIT 2026-07-21, lot N1 — SCORE É v1 : la marge cachée en euros.

Le classement que le client comprend sans explication : combien cette parcelle peut rapporter.

  marge_estimee = charge_fonciere_supportable − prix_probable_foncier

Table ADDITIVE `score_e`. Ne touche JAMAIS les tables servies. Univers : parcelles NON-ÉCARTÉES de
`q_v7_defisc`. Tout est **Estimé** — jamais un prix ni une promesse ; jamais de marge sur une écartée.

O0 (V2) — le prix de sortie n'est plus la médiane DVF de l'EXISTANT (~2 265 €/m², ancien dilué qui
écrasait 90 % des marges) mais le **prix de sortie NEUF** reconstruit par `dvf_prix_sortie_neuf`
(ventes ≤ 3 ans après achèvement d'un PC ; ~3 688 €/m² médian), avec repli secteur→commune→non estimable.
Un promoteur vend du neuf : c'est le prix économiquement juste pour une charge foncière de promotion.

Méthode (batch, hypothèses par DÉFAUT du bilan — cf. `faisabilite/bilan.py`) :
- **charge supportable** = bilan à REBOURS, version batch : `CA×coef − construction`, où
    CA = surf_habitable × prix_sortie_NEUF_secteur ; surf_habitable = SDP_résiduelle / coef_plancher (1,15) ;
    coef = 1 − (marge 9 % + frais 12 %) = 0,79 ; construction = SDP_résiduelle × 2 550 €/m² (milieu 2300-2800).
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

HYP_VERSION = "bilan-neuf-v2"          # O0 : prix de sortie NEUF · coef_plancher 1,15 · coef 0,79 · constr. 2550 €/m² · VRD 0
COEF_PLANCHER = 1.15
COEF_CA = 0.79
COUT_M2 = 2550.0
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
neuf_com AS (SELECT cle, prix_m2_neuf FROM dvf_prix_sortie_neuf WHERE niveau='commune')
SELECT p.idu,
       p.surface_m2,
       r.sdp_residuelle_m2 AS sdp,
       m.terrain,
       COALESCE(ns.prix_m2_neuf, nc.prix_m2_neuf) AS prix_vente,
       CASE WHEN ns.prix_m2_neuf IS NOT NULL THEN 'secteur'
            WHEN nc.prix_m2_neuf IS NOT NULL THEN 'commune' END AS niveau_prix
FROM parcel_p_score_v2 s
JOIN parcels p ON p.idu = s.parcelle_id
LEFT JOIN parcel_residuel r ON r.parcel_id = p.id
LEFT JOIN med m ON m.secteur = left(p.idu, 10)
LEFT JOIN neuf_sec ns ON ns.cle = left(p.idu, 10)
LEFT JOIN neuf_com nc ON nc.cle = left(p.idu, 5)
WHERE s.run_id = :run AND s.tier <> 'ecartee';
"""

_INSERT = """
INSERT INTO score_e (idu, estimable, marge_estimee, charge_supportable, prix_probable,
                     niveau_prix, hypotheses_version, libelle_court, detail, computed_at)
VALUES (:idu, :estimable, :marge, :charge, :prix, :niveau, :hv, :court, :detail, now())
ON CONFLICT (idu) DO UPDATE SET
  estimable = EXCLUDED.estimable, marge_estimee = EXCLUDED.marge_estimee,
  charge_supportable = EXCLUDED.charge_supportable, prix_probable = EXCLUDED.prix_probable,
  niveau_prix = EXCLUDED.niveau_prix, hypotheses_version = EXCLUDED.hypotheses_version,
  libelle_court = EXCLUDED.libelle_court, detail = EXCLUDED.detail, computed_at = now();
"""

_CAVEAT = ("Estimé (hypothèses de bilan génériques) — prix de sortie neuf médian DVF ≠ prix négocié ; "
           "hors coûts spécifiques (démolition, dépollution, VRD, stationnement, TVA, aléas). "
           "N'est ni un prix ni une promesse.")


def niveau_label(niveau_prix: str | None) -> str:
    """Libellé CLIENT du niveau du prix de sortie neuf (exigence Vic : niveau_prix visible).
    Tooltip/détail fiche + dossier banquier s'appuient dessus."""
    return {"secteur": "estimation niveau secteur",
            "commune": "estimation niveau commune (repli)"}.get(niveau_prix, "estimation niveau non déterminé")


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
        f"× 0,79 − construction 2 550 €/m²) ; prix probable = médiane terrain sectorielle × {surface_m2:.0f} m². {_CAVEAT}")
    return {"idu": idu, "estimable": True, "marge": marge, "charge": charge, "prix": prix,
            "niveau": niveau_prix, "hv": HYP_VERSION, "court": court, "detail": detail}


def build_score_e(session: Session, *, run: str = "q_v7_defisc",
                  commit: bool = True, log=lambda *_: None) -> dict:
    """Construit/rafraîchit `score_e` (rebuild complet idempotent). Lecture seule des sources.
    `commit=False` pour les tests transactionnels. Renvoie {'total', 'estimables'}."""
    session.execute(text("DROP TABLE IF EXISTS score_e"))
    session.execute(text(DDL))
    raw = session.execute(text(_SELECT_RAW),
                          {"run": run, "nt": N_MIN_TERRAIN, "nv": N_MIN_VENTE}).mappings().all()
    rows = [_row(r["idu"], r["surface_m2"], r["sdp"], r["terrain"], r["prix_vente"], r["niveau_prix"]) for r in raw]
    for r in rows:
        session.execute(text(_INSERT), r)
    if commit:
        session.commit()
    n_est = sum(1 for r in rows if r["estimable"])
    log(f"score_e : {len(rows)} parcelles non-écartées, {n_est} avec marge estimable")
    return {"total": len(rows), "estimables": n_est}
