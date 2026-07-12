# Annexe — reproductibilité (Phase 0, 12/07/2026)

Scripts complets (exécutés avec `LABUSE_DATABASE_URL=postgresql+psycopg://…/labuse`,
`.venv/bin/python`, seed 974, lecture seule) :
- `phase0_analyse.py` — lots 1 à 5 : partition acheteur/vendeur, recomputs V@T (miroir exact
  de `scripts/score-v/backtest.py`, sanity 0 écart / 20 768), lifts Katz, bandes, Fisher,
  labels L2/L3, snapshots, quadrants.
- `phase0b_compositions.py` — composition des combos de la bande 8-24 + décomposition du
  verrou « à surveiller ».

## Requêtes SQL principales (extraites des scripts)

```sql
-- MILLESIME_REF (constat en base)
SELECT millesime, count(*), max(date_import)::date FROM parcelle_personne_morale GROUP BY 1;
-- → 2025 · 82 701 · 2026-07-05 ; URL source : personnes_morales.py:26 (situation_2025)

-- natures DVF par an (LOT 3.1)
SELECT extract(year FROM date_mutation)::int, nature_mutation, count(DISTINCT id_parcelle)
FROM dvf_mutations_parcelle
WHERE date_mutation BETWEEN '2021-01-01' AND '2025-12-31'
GROUP BY 1, 2 ORDER BY 1, 2;

-- snapshots (LOT 4)
SELECT run_label, min(created_at), max(created_at), count(*)
FROM dryrun_parcel_evaluations GROUP BY 1 ORDER BY 2;
SELECT max(date_mutation) FROM dvf_mutations_parcelle;  -- 2025-12-31

-- Sitadel profondeur (LOT 5.1)
SELECT extract(year FROM date)::int, type, count(*) FROM sitadel_permits GROUP BY 1, 2;

-- quadrants (LOT 5.3) — définitions : src/labuse/scoring/dryrun.py (CASE matrice_statut)
SELECT d.matrice_statut, count(*), round(avg(d.q_score),1), round(avg(d.a_score),1),
       count(*) FILTER (WHERE vs.owner_type IN ('public','bailleur')),
       count(*) FILTER (WHERE vs.owner_type = 'pm')
FROM dryrun_parcel_evaluations d
JOIN parcels p ON p.id = d.parcel_id
LEFT JOIN parcel_v_score vs ON vs.parcelle_id = p.idu
WHERE d.run_label = 'q_v3_datagap' GROUP BY 1;

-- verrou « à surveiller » (LOT 5.3)
SELECT count(*),
       count(*) FILTER (WHERE a_score < 60)                                   AS a_bas,
       count(*) FILTER (WHERE a_score >= 60 AND COALESCE(a_completude,0) < 50) AS verrou_completude
FROM dryrun_parcel_evaluations
WHERE run_label = 'q_v3_datagap' AND matrice_statut = 'a_surveiller';
-- → 5 889 · 1 592 · 0  ⇒ le solde (4 297) échoue au verrou A_hors_zone (calculé au run,
--    non stocké — cf. dryrun.py : « le signal de zone ne bascule jamais seul »)

-- réfutation bâti/nu (LOT 5.3)
SELECT d.matrice_statut,
  round(100.0*count(*) FILTER (WHERE mv.idu IS NOT NULL AND COALESCE(rb.emprise_batie_m2,0) > 20)
        / NULLIF(count(*) FILTER (WHERE COALESCE(rb.emprise_batie_m2,0) > 20),0), 2) AS taux_vente_baties,
  round(100.0*count(*) FILTER (WHERE mv.idu IS NOT NULL AND COALESCE(rb.emprise_batie_m2,0) <= 20)
        / NULLIF(count(*) FILTER (WHERE COALESCE(rb.emprise_batie_m2,0) <= 20),0), 2) AS taux_vente_nues
FROM dryrun_parcel_evaluations d
JOIN parcels p ON p.id = d.parcel_id
LEFT JOIN parcel_residuel_bati rb ON rb.idu = p.idu
LEFT JOIN (SELECT DISTINCT id_parcelle idu FROM dvf_mutations_parcelle
           WHERE nature_mutation = 'Vente'
             AND date_mutation BETWEEN '2023-01-01' AND '2025-12-31') mv ON mv.idu = p.idu
WHERE d.run_label = 'q_v3_datagap' GROUP BY 1;
```

## Conventions statistiques
- Taux : IC95 Wilson. Lifts : point = taux(exposés)/taux(base cohorte) pour continuité avec
  l'extraction ; IC95 = RR de Katz **exposés vs non-exposés** (log-ratio, correction 0,5 si
  cellule nulle). Fisher exact bilatéral par énumération hypergéométrique.
- Cohorte enrichie 1 vendue : 4 non-vendues → seuls les RATIOS sont interprétables, aucun
  taux absolu n'est extrapolable au parc.
