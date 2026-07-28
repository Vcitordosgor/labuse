"""O0 — Score É V2 : PRIX DE SORTIE NEUF par commune (déblocage du Score É).

Reconstruit le prix de sortie NEUF **du collectif de MARCHÉ** depuis les ventes récentes identifiées.

MANDAT CALIBRATION ESTIMÉES — instrument révisé (décision Vic 28/07/2026, back-test contre le réel
`CALIBRATION_PHASE_A_BACKTEST.md`). Le back-test a montré que la médiane de TOUTES les ventes
(maisons + appartements, tous financements) sous-évaluait massivement le prix du collectif de
marché : la médiane noyait le collectif sous des maisons individuelles et du logement aidé, et
déclarait non viables 78 % des opérations réellement construites. L'instrument correct isole le
collectif de marché :

  - **APPARTEMENTS uniquement** (proxy du collectif ; les maisons sont un autre marché) ;
  - **hors bailleurs sociaux** : on EXCLUT les ventes issues d'une opération de bailleur social /
    SEM (LLS/LLTS à prix plafonné) — identifiées par le pétitionnaire du PC d'origine sur la
    parcelle (`SOCIAL_SIREN`). C'est une correction de POPULATION (le quartile bas des communes
    concentrait l'aidé — 41 % vs 6 % ailleurs), pas un réglage de percentile : on prend ensuite
    la MÉDIANE de marché, pas un p75 arbitraire ;
  - **N_MIN ≥ 10** ventes (marché observable) ;
  - **règle de fragilité** (Vic §1) : un N_MIN franchi de justesse (n < `N_FRAGILE`) combiné à une
    médiane SOUS le seuil de bascule (`SEUIL_BASCULE` 3 859 €/m² habitable — le prix minimal pour
    couvrir construction + marge avant tout foncier) est un signal d'INSTRUMENT NON FIABLE, pas
    une commune non viable → écarté (« non calculable »). Écarte La Possession (n=12, 2 638).

Source « neuf » : ventes (`Vente`) d'un appartement réalisées **≤ 3 ans après l'achèvement d'un
PC** (proxy VEFA/livraison). €/m² borné [1000 ; 12000] (anti-artefact DVF).

Repli : **secteur (préfixe IDU 10) si retenu**, sinon **commune (INSEE 5) si retenue**, sinon
absent (→ « non calculable » côté score_e et bilan cœur). Table ADDITIVE `dvf_prix_sortie_neuf`.
Lecture seule des sources ; ne touche jamais les runs servis.

Couverture attendue au 28/07/2026 : **5 communes** — Saint-Denis, Saint-Pierre, Saint-Paul,
Saint-Leu, Le Tampon (les seules où un marché du collectif neuf est observable). Ailleurs, LABUSE
dit qu'il ne sait pas.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

N_MIN = 10          # ventes d'appartements neufs de marché minimum pour une médiane
N_FRAGILE = 20      # sous ce n, une médiane sous le seuil de bascule est jugée non fiable (écartée)
SEUIL_BASCULE = 3859  # €/m² habitable : couvrir construction (1,15×2550) + marge (coef 0,76) avant foncier

# Bailleurs sociaux / SEM réunionnais (SIREN confirmés) — leurs ventes (LLS/LLTS à prix plafonné)
# sont EXCLUES du prix de marché. Faux positifs de nom écartés (mesure back-test §9/§20).
SOCIAL_SIREN = (
    "310895172",  # SHLMR
    "310863592",  # SIDR
    "380177170",  # SODEGIS
    "310863378",  # SEDRE (SEM départementale)
    "380572453",  # SEMADER
    "332824242",  # SEM Réunion (aménagement)
    "378918510",  # SODIAC (SEM Saint-Denis)
)

DDL = """
CREATE TABLE IF NOT EXISTS dvf_prix_sortie_neuf (
  cle           varchar(10) NOT NULL,   -- secteur (préfixe IDU 10) OU INSEE commune (5)
  niveau        text NOT NULL,          -- 'secteur' | 'commune'
  prix_m2_neuf  int  NOT NULL,          -- médiane €/m² habitable, appartements neufs de MARCHÉ (hors social)
  n             int  NOT NULL,          -- nb de ventes ayant servi
  computed_at   timestamptz DEFAULT now(),
  PRIMARY KEY (cle, niveau)
);
"""

_BUILD = """
WITH ach AS (
  SELECT pmp.idu, min(md.date_achevement) AS ach FROM p_model_permits pmp
  JOIN m10_permit_delais md ON md.permit_id = pmp.permit_id
  WHERE pmp.type = 'PC' AND md.date_achevement IS NOT NULL GROUP BY pmp.idu),
muts AS (
  SELECT id_parcelle idu, date_mutation::date dt, valeur_fonciere val, surface_reelle_bati surf, type_local tl
  FROM dvf_mutations_histo WHERE nature_mutation = 'Vente'
  UNION ALL
  SELECT id_parcelle, date_mutation::date, valeur_fonciere, surface_reelle_bati, type_local
  FROM dvf_mutations_parcelle WHERE nature_mutation = 'Vente'),
neuf AS (
  SELECT left(m.idu, 10) AS secteur, left(m.idu, 5) AS insee, m.val / m.surf AS prix_m2
  FROM muts m JOIN ach a ON a.idu = m.idu
  WHERE m.surf >= 20 AND m.val > 20000 AND m.tl = 'Appartement'
    AND m.dt >= a.ach AND m.dt < a.ach + INTERVAL '3 years'
    AND m.val / m.surf BETWEEN 1000 AND 12000
    -- EXCLUSION des ventes issues d'une opération de bailleur social / SEM (prix plafonné)
    AND NOT EXISTS (
      SELECT 1 FROM sitadel_permits s
      WHERE s.idu_codes ? m.idu AND s.raw->>'petitioner_siren' = ANY(:social))),
agg AS (
  SELECT secteur AS cle, 'secteur' AS niveau,
         round(percentile_cont(0.5) WITHIN GROUP (ORDER BY prix_m2))::int AS p, count(*) AS n
  FROM neuf GROUP BY secteur HAVING count(*) >= :nmin
  UNION ALL
  SELECT insee AS cle, 'commune' AS niveau,
         round(percentile_cont(0.5) WITHIN GROUP (ORDER BY prix_m2))::int AS p, count(*) AS n
  FROM neuf GROUP BY insee HAVING count(*) >= :nmin)
INSERT INTO dvf_prix_sortie_neuf (cle, niveau, prix_m2_neuf, n, computed_at)
SELECT cle, niveau, p, n, now() FROM agg
-- règle de fragilité : n franchi de justesse ET médiane sous le seuil de bascule → écarté
WHERE NOT (n < :nfragile AND p < :seuil);
"""


# ── Résolution du prix de sortie servi (préséance + motif « non calculable ») ────────────────
# Communes où le collectif est MAJORITAIREMENT social/aidé (part sociale ≥ 50 % du collectif
# identifié, mesure back-test §12) — le bilan de MARCHÉ y est structurellement inapplicable.
SOCIAL_DOMINANT_INSEE = frozenset({
    "97407",  # Le Port 96 %
    "97403",  # Entre-Deux 97 %
    "97417",  # Saint-Philippe 84 %
    "97405",  # Petite-Île 76 %
    "97424",  # Cilaos 72 %
    "97402",  # Bras-Panon 60 %
    "97412",  # Saint-Joseph 56 %
    "97406",  # La Plaine-des-Palmistes 53 %
})


def motif_non_calculable(insee: str | None) -> str:
    """Formulation CLIENT du « non calculable » selon le cas (formulations Vic 28/07/2026).
    Le patrimonial (build-to-hold) est un motif d'OPÉRATION, pas de commune — traité côté fiche."""
    if insee in SOCIAL_DOMINANT_INSEE:
        return ("Charge foncière de marché non atteignable sur cette commune — le collectif y est "
                "majoritairement social ou aidé.")
    return ("Marché du collectif neuf non observable sur cette commune (ventes d'appartements de "
            "marché insuffisantes) — charge non calculable.")


def resolve_prix_neuf_marche(session: Session, parcel_id: int,
                             bassin_override: dict | None = None) -> tuple[float | None, str | None, str | None]:
    """Prix de sortie neuf SERVI pour une parcelle, préséance (décision Vic 28/07/2026) :
    override bassin SOURCÉ > `dvf_prix_sortie_neuf` secteur > commune > **non calculable**.
    Renvoie (prix €/m² | None, niveau | None, motif_non_calculable | None). Le socle global 4900
    n'existe plus : hors des 5 communes couvertes, on dit qu'on ne sait pas (jamais un chiffre faux)."""
    if (bassin_override and bassin_override.get("provenance") == "sourcee"
            and (bassin_override.get("value") or 0) > 0):
        return float(bassin_override["value"]), "override_bassin", None
    row = session.execute(text(
        "SELECT d.prix_m2_neuf AS p, d.niveau AS niveau, left(pa.idu, 5) AS insee "
        "FROM parcels pa "
        "LEFT JOIN dvf_prix_sortie_neuf d ON d.cle IN (left(pa.idu, 10), left(pa.idu, 5)) "
        "WHERE pa.id = :pid ORDER BY (d.niveau = 'secteur') DESC NULLS LAST LIMIT 1"),
        {"pid": parcel_id}).first()
    if row and row.p is not None:
        return float(row.p), row.niveau, None
    return None, None, motif_non_calculable(row.insee if row else None)


def build_prix_neuf(session: Session, *, commit: bool = True, log=lambda *_: None) -> dict:
    """Construit/rafraîchit `dvf_prix_sortie_neuf` (rebuild complet idempotent). Renvoie {'secteurs','communes'}."""
    session.execute(text("DROP TABLE IF EXISTS dvf_prix_sortie_neuf"))
    session.execute(text(DDL))
    session.execute(text(_BUILD),
                    {"nmin": N_MIN, "nfragile": N_FRAGILE, "seuil": SEUIL_BASCULE,
                     "social": list(SOCIAL_SIREN)})
    if commit:
        session.commit()
    r = session.execute(text(
        "SELECT niveau, count(*) FROM dvf_prix_sortie_neuf GROUP BY niveau")).all()
    counts = {niveau: n for niveau, n in r}
    log(f"dvf_prix_sortie_neuf : {counts.get('secteur', 0)} secteurs + {counts.get('commune', 0)} communes "
        f"(appartements de marché, hors bailleurs sociaux, n ≥ {N_MIN})")
    return {"secteurs": counts.get("secteur", 0), "communes": counts.get("commune", 0)}
