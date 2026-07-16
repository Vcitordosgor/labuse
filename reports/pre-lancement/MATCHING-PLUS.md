# MATCHING PROMOTEUR PLUS (point 34) · `feat/matching-plus`

**Back + front. Zéro touche scoring.** Honnêteté démo/réel, privacy tenue.

## Lot 0 — Constat
`match_profiles` = **2 profils DÉMO (`demo=true`, fictifs)** ; match binaire sur commune/surface/SDP
contre les bascules `event_log`. **SITADEL (`sitadel_permits`, 50 043 permis)** porte le **déposant** :
`raw->>'petitioner_name'` + **`petitioner_siren`** (**9 087 permis avec SIREN = personnes morales**),
géolocalisé (commune sur 50 043, geom sur 39 294). → **C réalisable et RÉEL.**

## Lot 1+2 — Pourquoi + score (A, B)
`GET /partners/match/compatibilite/{idu}` : par profil, **score 0-100 DÉCOMPOSÉ** (surface 30 · SDP 30 ·
commune 20 · constructible U/AU 10 · signal chaude 10) avec **les critères qui collent** (✓/○ + valeur).
Fini le oui/non opaque. **Profils clairement labellisés DÉMO · ILLUSTRATIF.**

## Lot 3 — Promoteurs actifs réels (C)
`GET /partners/promoteurs-actifs?commune=` : **promoteurs (personnes morales) ayant déposé des permis
dans les 5 dernières années** dans le secteur, via **SITADEL** — nom, **SIREN**, nb permis, logements.
Donnée **RÉELLE**, bloc **visuellement distinct** (badge vert « RÉEL · SITADEL » vs violet « DÉMO »).
Preuve : Saint-Paul → SEDRE (SIREN 310863378, 56 permis, 238 logts), SODIAC HLM (252 logts)…

## PRIVACY (ligne rouge)
Bloc réel : **filtré aux déposants avec SIREN (personnes morales, public)** — les particuliers ne sont
**JAMAIS exposés** (exclus par `petitioner_siren ~ '^[0-9]{9}$'`).

## Honnêteté démo/réel
- Compatibilité + profils = **DÉMO · ILLUSTRATIF** (badge violet).
- Promoteurs actifs = **RÉEL · SITADEL** (badge vert). Source citée dans le bloc.

## Preuve
`matching-plus.png` — compatibilité (2 profils démo, scores 60/100 décomposés) + promoteurs actifs réels
(SITADEL, PM nommées + SIREN). Distinction démo/réel nette.

## Non-régression & garanties
`tsc`/build verts, endpoints testés. **Zéro touche scoring/cascade/run.** `git diff` = `partners.py`
(2 endpoints), `moteurs.tsx` (M19), `lib/api.ts` (clients), QA.
