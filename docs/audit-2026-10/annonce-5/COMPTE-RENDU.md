# ANNONCE-5 — Refonte du PDF « Analyse d'annonce » (maquette v2)

**Branche** `feat/annonce-5` (worktree `~/Desktop/labuse-annonce5`, base `origin/main` `17280eb21`).
Ports recette : API 8970 / Vite 6170. Aucun accès prod, rien de servi touché, aucune session créée.
Merge = geste de Vic.

## Objectif

Refondre le document « Analyse d'annonce » (outil ET Docs, même route → PDF identiques) selon la
maquette validée : **variante parcelle sur 2 pages**, **variante lien sur 1 page**. La maquette fixe la
structure ; toutes les valeurs viennent des données servies. Aucune photo d'annonce, jamais.

Doctrine tenue : **un seul point de données par variante** (`pige.api.rapport_parcelle` /
`rapport_lien`), lu À LA FOIS par l'écran et par le PDF → **l'outil et le PDF ne divergent jamais**.

## Ce qui a été fait

### Variante parcelle (adresse), 2 pages
- **En-tête** : titre = adresse ; sous-titre = IDU · zone · surface · nature (nue / bâtie, maison ou
  appartement — le type bâti est déduit du **secteur dominant** des ventes DVF, règle de nature de la fiche).
- **Deux cartes côte à côte** : l'ortho existante + une **carte cadastrale neuve** (`plan_zonage`,
  `api/plan_situation.py`) 100 % vectorielle depuis les couches servies (`spatial_layers` : parcelles
  voisines = cadastre, zonage PLU en aplats, aléas en aplats sable, parcelle en menthe). Hors réseau,
  déterministe. Étiquettes zone/aléa posées en HTML (nettes).
- **6 tuiles** : surface, zone PLU, SDP restante, classement, risques, exposition.
- **Estimation** (gauche) : €/m², fourchette (Q1–Q3), fiabilité, source (N ventes · rayon · période).
  **Valeur indicative** (droite) : surface du bâti (ou du terrain) × €/m² + fourchette + **repère
  terrain nu du secteur**. Le comparateur suit le type (maison↔maisons, appartement↔appartements,
  terrain nu↔terrains).
- **Tableau des 8 ventes les plus proches** (date, type, surface, prix, €/m², distance) + le nombre
  total retenu. Mêmes ventes et même total que l'estimation (voir « point unique » ci-dessous).
- **Page 2 — Le foncier** : règles de la zone (hauteur, emprise, reculs, stationnement, **depuis le
  calibrage** `resolve_zone`) FACE aux mesures de la parcelle (assiette constructible aléa déduit,
  emprise du bâti, hauteurs LiDAR faîtage/égout + date de survol, SDP restante) + phrase de classement
  (vocabulaire gravé). **Risques et contraintes** (aléa, niveau, document, implication — tirés de la
  fiche). **Le marché de la commune** (ventes 12 mois, médianes maison/appartement/terrain, évolution
  12 mois, graphique 5 ans). **Ce qu'il reste à vérifier** (≤ 3 points dérivés des données).

### Variante lien (commune), 1 page
- **Faits de l'annonce** + lien « Voir l'annonce → » + **extrait de description** (2 lignes max, SEULEMENT
  s'il est en base ; sinon rien).
- **Deux lectures côte à côte, chiffrées** : lecture bâti (écart % au repère du type dans la commune) et
  lecture foncière (terrain × terrain nu, en % du prix demandé). La phrase « valeur surtout foncière »
  devient une **conclusion chiffrée** sous la lecture foncière.
- **Bloc commune complet** : ventes, médianes, évolution, PLU, aléas, permis déposés 12 mois.
- **Encart** vers le rapport complet sur 2 pages.

### Le bug « commune vide » de La Possession (29/10) — corrigé
**Cause** : les lookups commune en aval (`commune_contexte_cache`, `fiche_commune.comparable`) sont
**sensibles à la casse** ; l'entrée lien pouvait recevoir `« la possession »` (Leboncoin) quand la base
porte `« La Possession »` → cache manqué → chemin dégradé / bloc vide.
**Correctif** : normalisation **à la source** (`_commune_canonique` lit `communes_referentiel`, repli
`parcels`) dans `radar_annonce_analyser` + tout le nouveau bloc commune (`marche_commune_bloc`) est
**insensible à la casse** (`lower(commune) = lower(:c)`). Vérifié : `« la possession »`, `« LA
POSSESSION »` et `« La Possession »` donnent le MÊME bloc rempli.

## Architecture (le « point unique » écran == PDF)

- `marche_service.comparateur_bien(db, idu)` — **une seule requête DVF** ancrée sur la parcelle → l'agrégat
  (médiane, Q1/Q3, n retenues, rayon effectif adaptatif 500→1000→1500→commune, période, fiabilité) ET les
  8 ventes les plus proches ET le total. Garantit estimation = valeur indicative = tableau, sans divergence.
- `faisabilite.marche_commune.marche_commune_bloc(db, commune)` — médianes par type, évolution 12 mois,
  série annuelle 5 ans, permis 12 mois (fichier déjà déclaré lecteur DVF/Sitadel → aucune nouvelle arête
  au verrou de graphe).
- `pige.api.estimation_annonce` (réécrit), `rapport_parcelle`, `rapport_lien` + endpoints
  `/radar/annonce/estimation/{idu}`, `/radar/annonce/rapport/{idu}`, `/radar/annonce/analyser` (enrichi).
- Verrou de graphe `test_graphe_exact_dans_les_deux_sens` : **vert** (toutes les lectures DVF nouvelles
  sont dans des fichiers déjà déclarés ; `spatial_layers` est exempt du verrou).

## Garde-fous (mandat)

Jamais un champ vide imprimé (une donnée absente fait disparaître sa ligne/tuile) · formats français ·
aucun code brut · aucun texte coupé · parcelle entière sur les cartes (`_choisir_cadre_plan`) ·
classement lu sur le run SERVI (`score_labuse`, q_v20) · horloge via `labuse.tz`. CSS **scopé** au seul
document (`page_extra_css`) → les 8 autres documents servis sont inchangés.

## Recette (base servie Mac `postgresql:///labuse`, lecture seule, run q_v20)

PDF générés **via les routes HTTP réelles** (l'outil et Docs tapent la MÊME route → identiques) :
- `pdf/recette-BZ1065.pdf` — parcelle **bâtie, maison, 2 pages** (HTTP 200).
- `pdf/recette-CX0800.pdf` — parcelle **nue, 2 pages** (HTTP 200).
- `pdf/recette-lapossession.pdf` — **lien**, annonce Radar `3251185886`, **1 page** (HTTP 200) ; bloc
  commune REMPLI (preuve du correctif).
- **outil == Docs** : 2ᵉ appel de la même route → texte pdftotext **md5 identique**.
- **PDF == écran** : endpoint `/radar/annonce/estimation/97411000BZ1065` → médiane 3528, valeur
  indicative 695 016 €, n_total 42, 8 comparables ; le PDF imprime EXACTEMENT ces chiffres.
- Captures écran : `png/ecran-parcelle-accordeon-ouvert.png` (accordéon « Les ventes comparables (42) »
  OUVERT, table + valeur indicative) et `png/ecran-lien-deux-lectures.png` (lectures −19 % / 288 666 € +
  bloc commune). Rendus PNG des 3 PDF dans `png/`.

## Vérifications

- `tsc -b` : **0**.
- `vitest` : **301/301**.
- `pytest` famille hook (`not db and not local and not reel and not network`) : **2710 passed, 59 skipped,
  0 failed** (dont `test_annonce_pdf.py` **15/15** réécrit pour la nouvelle API + verrou de graphe 4/4).

## Fichiers touchés

Backend : `marche_service.py` (comparateur_bien) · `faisabilite/marche_commune.py` (marche_commune_bloc
+ helpers) · `pige/api.py` (estimation_annonce réécrit, rapport_parcelle, rapport_lien, _commune_canonique,
helpers foncier/risques/classement/à-vérifier, endpoints) · `api/plan_situation.py` (plan_zonage) ·
`api/documents.py` (route lien → rapport enrichi) · `exports/builder.py` (construire_* + cartes + CSS
scopé) · `exports/blocs/annonce.py` (rendu_parcelle / rendu_lien, refonte complète).
Frontend : `lib/api.ts` (types) · `components/outils/AnalyserAnnonce.tsx` (valeur indicative, accordéon
comparables, deux lectures). Tests : `tests/test_annonce_pdf.py`.

## À noter

- Variante parcelle **nue** : pas de tableau de comparables bâti (les ventes de terrain nu ne portent
  pas de distance exploitable dans `dvf_mutations`) ; le repère secteur (n réel) tient lieu d'échantillon,
  et la valeur indicative = contenance × repère terrain nu. Choix assumé, sans divergence.
- La carte de la variante lien est un repère NEUTRE à l'échelle de la commune (le mandat écarte le
  rattachement parcellaire de l'entrée lien) ; sa légende le dit.
- ⚠ venv éditable `~/Desktop/labuse/.venv` → `labuse-main/src` : lancer avec `PYTHONPATH=…annonce5/src`.
  Relancer uvicorn après édition (pas de `--reload`).
