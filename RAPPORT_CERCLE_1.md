# RAPPORT — Cercle 1 « Fondations métier » (LA BUSE v3)

> Les 3 items qui font qu'un promoteur DÉCIDE. Rapports de dispo : `RAPPORT_DISPO_1A.md`,
> `RAPPORT_DISPO_1B.md`. **262 tests verts**, ruff clean, démo 8/8, baseline 3 000.

## 1.A — Propriétaire (vraie donnée DGFiP publique) ✅
- Source : DGFiP « parcelles des personnes morales », **Licence Ouverte v2**, millésime 2025, 974
  confirmé. Loader idempotent (table `parcelle_personne_morale`, source/millésime tracés).
- **12 539 parcelles morales Saint-Paul** chargées ; **984/3 000** de notre référentiel ont un
  propriétaire morale identifié (CBO Territoria, communes, EPF Réunion, bailleurs, SEM…).
- Classifieur `groupe DGFiP (0-9) + forme juridique → owner_type` (commune/État/collectivité/EPF/
  établissement public/SEM/bailleur/SCI/société/copropriété). **Fusionne C3** : badge fiche +
  filtre carte (public 493 / privé 490 / inconnu 2012) + **owner_name réel**. Absente du fichier
  = particulier → **bouton SPF** (aucune donnée perso). Recette 3 cas ✅.

## 1.B — Historique SITADEL (nature + statut + dynamique) ✅
- Enrichit C4. Dispo : Région ODS, 2 529 autorisations ; pas de lat/lon → géoloc par réf.
  cadastrale (117/2 519 dans le référentiel bbox — limite documentée, jamais de placement au hasard).
- Fiche : **nature** (« N logements · ~X m² »), **statut** (« autorisé le … · travaux achevés » —
  ces flux n'ont pas les refus, jamais inventés), et **indicateur de dynamique de secteur**
  (autorisations + logements récents < 5 ans → actif/modéré/calme). Recette ✅ (BI0197 actif).

## 1.C — Calibration du bilan (params éditables par secteur) ✅
- **Tous les paramètres** du bilan déclarés une fois (`bilan_params.py`), groupés (Recettes / Coûts /
  Frais & marge), éditables et **persistés par SECTEUR** (bassin PLU) : prix neuf override,
  prix LLS, ratio vendable, coût construction, **VRD base + majorations pente/assainissement**,
  honoraires, **frais financiers**, marge cible.
- Résolution **défaut ← global ← secteur** ; override saisi = plus « placeholder ». Paramètres
  **critiques non calibrés** → bandeau « bilan non fiable » sur la fiche. Endpoints `GET/POST
  /bilan/params`. UI : panneau de calibration par secteur (badges « non calibré », recalcul).
- **Le code n'invente rien** : Vic calibre (session terrain). Recette ✅ : un override de secteur
  recalcule le bilan des parcelles de CE secteur uniquement (isolation + override global vérifiés).

## ⛔ STOP & VALIDATE — fin Cercle 1
Reste **dépendances Vic** : calibrer les vraies valeurs du bilan (1.C, session terrain) ;
whitelist PEIGEO (pour Cercle 2 — 2.D/2.E) ; décision clé API (Cercle 3 — 3.A). Sur ta validation,
j'enchaîne le **Cercle 2** (2.A pente → 2.B vue mer → 2.C ravines [déjà fait C1, reste la nuance
axe/bord] → 2.D 50 pas → 2.E assainissement).
