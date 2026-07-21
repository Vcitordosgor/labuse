"""EXTRACT-DÉPOSANTS-ACTIFS — CSV de prospection des PM qui déposent des PC/PA en ce moment.

READ-ONLY (aucune table créée, zéro touche scoring). Un déposant actif = une PERSONNE MORALE ayant
déposé au moins un PC/PA dans la fenêtre (24 mois par défaut) — identifiée par le SIREN pétitionnaire
du fichier SITADEL SDES (couverture partielle : le SIREN n'est présent que sur une partie des permis,
on n'extrapole pas). Enrichissements, tous Sourcés :
  · RNE (`pm_dirigeants`) : dirigeants **actifs ET diffusibles uniquement** — le flag de non-diffusion
    RNE prime, un dirigeant non diffusible n'apparaît JAMAIS dans le CSV (428 exclus au 21/07/2026) ;
    rôle livré en code RNE brut (pas de libellé inventé) ;
  · DGFiP (`parcelle_personne_morale`) : nombre de parcelles détenues (contexte foncier).

CONFIDENTIALITÉ (précisions Vic 21/07/2026) : le CSV vit dans `exports/` (gitignoré) — les données
nominatives ne vont JAMAIS en git ; dirigeants RNE autorisés dans le CSV ; particulier jamais inféré.
"""
from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

MOIS_DEFAUT = 24

COLONNES = ["siren", "denomination", "n_permis", "n_pc", "n_pa", "dernier_depot", "communes",
            "nb_logements", "n_parcelles_detenues", "dirigeants", "source"]

_SQL = """
WITH permis AS (
  SELECT raw->>'petitioner_siren' AS siren,
         (array_agg(raw->>'petitioner_name' ORDER BY date DESC))[1] AS denomination,
         count(*) AS n_permis,
         count(*) FILTER (WHERE type = 'PC') AS n_pc,
         count(*) FILTER (WHERE type = 'PA') AS n_pa,
         max(date)::date AS dernier_depot,
         string_agg(DISTINCT commune, ' ; ') AS communes,
         sum(CASE WHEN raw->>'nb_lgt' ~ '^[0-9]+(\\.[0-9]+)?$'
                  THEN (raw->>'nb_lgt')::numeric ELSE NULL END)::int AS nb_logements
  FROM sitadel_permits
  WHERE raw ? 'petitioner_siren' AND raw->>'petitioner_siren' ~ '^[0-9]{9}$'
    AND type IN ('PC', 'PA')
    AND date >= CURRENT_DATE - make_interval(months => :mois)
  GROUP BY 1),
fonc AS (
  SELECT siren, count(DISTINCT idu) AS n_parcelles
  FROM parcelle_personne_morale WHERE siren IS NOT NULL GROUP BY 1),
-- dirigeants RNE : actifs ET diffusibles UNIQUEMENT (le flag de non-diffusion prime)
dirs AS (
  SELECT siren, string_agg(trim(nom || ' ' || coalesce(prenoms, '')) ||
                           ' (rôle RNE ' || coalesce(role_entreprise::text, '?') || ')',
                           ' ; ' ORDER BY nom) AS dirigeants
  FROM pm_dirigeants WHERE actif AND diffusible GROUP BY 1)
SELECT p.siren, p.denomination, p.n_permis, p.n_pc, p.n_pa, p.dernier_depot, p.communes,
       p.nb_logements, coalesce(f.n_parcelles, 0) AS n_parcelles_detenues, d.dirigeants
FROM permis p
LEFT JOIN fonc f ON f.siren = p.siren
LEFT JOIN dirs d ON d.siren = p.siren
ORDER BY p.n_permis DESC, p.dernier_depot DESC;
"""


def extract_deposants(session: Session, *, mois: int = MOIS_DEFAUT) -> list[dict]:
    """Extrait les déposants actifs (une ligne par SIREN). Read-only."""
    rows = session.execute(text(_SQL), {"mois": mois}).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        d["dernier_depot"] = str(d["dernier_depot"]) if d["dernier_depot"] else None
        d["source"] = "SITADEL SDES (permis) · RNE (dirigeants diffusibles) · DGFiP (foncier)"
        out.append(d)
    return out


def write_csv(rows: list[dict], path: str | Path) -> Path:
    """Écrit le CSV dans `exports/` (gitignoré — jamais en git)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES, delimiter=";")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in COLONNES})
    return path
