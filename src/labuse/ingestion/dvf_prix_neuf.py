"""O0 — Score É V2 : PRIX DE SORTIE NEUF par secteur (déblocage du Score É).

La note de sensibilité (clôture cycle 2) a montré que le prix de sortie des médianes DVF de l'EXISTANT
(~2 265 €/m², ancien + maisons diluées) écrase 90 % des marges — un promoteur vend du NEUF (~3 688 €/m²).
Ce module reconstruit le prix de sortie NEUF par secteur depuis les ventes récentes identifiées.

Source « neuf » : ventes (`Vente`, avec surface bâtie) d'un logement (Maison/Appartement) réalisées
**≤ 3 ans après l'achèvement d'un PC** (proxy VEFA/livraison — les VEFA pures sont sans surface au 974,
d'où le proxy achèvement). €/m² borné [1000 ; 12000] (anti-artefact DVF, mêmes bornes que bilan.py).

Repli documenté : **secteur (préfixe IDU 10) si n ≥ 5**, sinon **commune (INSEE 5) si n ≥ 5**, sinon absent
(→ « non estimable » côté score_e). Table ADDITIVE `dvf_prix_sortie_neuf` (cle, niveau, prix_m2_neuf, n).
Lecture seule des sources ; ne touche jamais les runs servis.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

N_MIN = 5     # ventes neuves minimum pour une médiane sectorielle/communale

DDL = """
CREATE TABLE IF NOT EXISTS dvf_prix_sortie_neuf (
  cle           varchar(10) NOT NULL,   -- secteur (préfixe IDU 10) OU INSEE commune (5)
  niveau        text NOT NULL,          -- 'secteur' | 'commune'
  prix_m2_neuf  int  NOT NULL,          -- médiane €/m² habitable, ventes neuves (Sourcé DVF)
  n             int  NOT NULL,          -- nb de ventes neuves ayant servi
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
  WHERE m.surf >= 20 AND m.val > 20000 AND m.tl IN ('Maison', 'Appartement')
    AND m.dt >= a.ach AND m.dt < a.ach + INTERVAL '3 years'
    AND m.val / m.surf BETWEEN 1000 AND 12000)
INSERT INTO dvf_prix_sortie_neuf (cle, niveau, prix_m2_neuf, n, computed_at)
SELECT secteur, 'secteur', round(percentile_cont(0.5) WITHIN GROUP (ORDER BY prix_m2))::int, count(*), now()
FROM neuf GROUP BY secteur HAVING count(*) >= :nmin
UNION ALL
SELECT insee, 'commune', round(percentile_cont(0.5) WITHIN GROUP (ORDER BY prix_m2))::int, count(*), now()
FROM neuf GROUP BY insee HAVING count(*) >= :nmin;
"""


def build_prix_neuf(session: Session, *, commit: bool = True, log=lambda *_: None) -> dict:
    """Construit/rafraîchit `dvf_prix_sortie_neuf` (rebuild complet idempotent). Renvoie {'secteurs','communes'}."""
    session.execute(text("DROP TABLE IF EXISTS dvf_prix_sortie_neuf"))
    session.execute(text(DDL))
    session.execute(text(_BUILD), {"nmin": N_MIN})
    if commit:
        session.commit()
    r = session.execute(text(
        "SELECT niveau, count(*) FROM dvf_prix_sortie_neuf GROUP BY niveau")).all()
    counts = {niveau: n for niveau, n in r}
    log(f"dvf_prix_sortie_neuf : {counts.get('secteur', 0)} secteurs + {counts.get('commune', 0)} communes (n ≥ {N_MIN})")
    return {"secteurs": counts.get("secteur", 0), "communes": counts.get("commune", 0)}
