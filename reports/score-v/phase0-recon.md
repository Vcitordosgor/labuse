# Phase 0 — Recon Score V (10/07/2026) — GO/NO-GO par signal

| Check | Verdict | Détail |
|---|---|---|
| P1 DVF | **GO partiel** | Géo-DVF 974 chargé niveau parcelle → `dvf_mutations_parcelle` (102 551 lignes 2021→2025, 37 868 parcelles, 98,5 % jointes ; `dvf_mutations` cascade intouchée). **Millésimes 2014-2020 retirés de la distribution officielle (fenêtre glissante 5 ans DGFiP)** → `DVF_TENURE_12`/`DVF_TENURE_8` **NO-GO** tels que définis. Option à trancher au GO : variante dégradée « aucune mutation sur fenêtre observable 5 ans » à 8 pts (code `DVF_TENURE_OBS5`), sinon famille D = friche + terrain nu seulement. Malus achat récent < 3 ans : GO. Backtest (cohorte 2023-2025) : GO. |
| P2 BODACC | **GO** | Connecteur ODS par SIREN déjà en place (passe île 05/07 : 662 annonces PC / 191 SIREN sur 9 733) ; API testée OK ce jour. Nouvelle passe familles radiations + ventes-cessions → `bodacc_annonces_owner` en Phase 2. |
| P3 DGFiP PM | **GO** | 82 701 liens parcelle↔PM, SIREN valide 87,7 % (9 733 distincts) ≥ seuil 70 %. Fallback dénomination pour les ~10 100 liens restants. ⚠ Pas d'adresse siège dans DGFiP PM → famille C (géo) calculée via siège recherche-entreprises (API testée OK). |
| P4 Dirigeants | **GO** | RNE en base : année de naissance OK (`YYYY-MM`), 9 337/9 733 SIREN couverts (95,9 %). État administratif (cessation/sommeil) **absent** de la vague RNE → complément recherche-entreprises par SIREN (throttle ~7 req/s, cache `owner_enrichment`). 731 gigognes non résolues (429 INPI) : pas de signal âge pour elles. |
| P5 DPE | **GO best-effort** | Match parcelle 95,2 % (866/910) ≥ seuil 50 %. Mais base ADEME 974 intrinsèquement mince : 910 DPE, **43 F/G sur toute l'île** → famille E rare mais fiable. |

Cartofriches : 372 friches en base (famille D OK). Matrice Q×A de référence : run `q_v2` = 431 663 parcelles, **1 083 chaudes**.
