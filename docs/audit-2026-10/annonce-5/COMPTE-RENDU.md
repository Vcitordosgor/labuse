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

- Variante parcelle **nue** : le tableau des comparables montre les ventes de TERRAIN NU les plus proches
  (via `dvf_mutations_parcelle`, cf. ANNONCE-5-FIX §5) ; l'estimation reste le repère secteur (n réel) et
  la valeur indicative = surface × repère terrain nu. Les deux périmètres (secteur pour le repère, rayon
  pour le tableau) sont tous deux étiquetés.
- La carte de la variante lien est un repère NEUTRE à l'échelle de la commune (le mandat écarte le
  rattachement parcellaire de l'entrée lien) ; sa légende le dit.
- ⚠ venv éditable `~/Desktop/labuse/.venv` → `labuse-main/src` : lancer avec `PYTHONPATH=…annonce5/src`.
  Relancer uvicorn après édition (pas de `--reload`).

---

# ANNONCE-5-FIX — retours de Vic sur les 3 PDF

Même branche `feat/annonce-5`, même worktree, pas de merge.

## Constats traités

1. **Valeur indicative bâtie = ORDRE DE GRANDEUR.** La surface habitable n'est pas connue : la ligne dit
   désormais « D'après l'emprise au sol BD TOPO (197 m²) × 3 528 €/m² », fourchette **élargie par l'écart
   mesuré du segment** (±32 % maison), et une note « Ordre de grandeur, pas un calcul exact ». **Tous les
   montants en € arrondis au millier**, fourchettes comprises (`_arrondi_mille`).
2. **SDP restante BZ1065 (35 → 26).** Cause : le champ `potentiel_transformation.sdp_residuelle_m2` est
   **recalculé en direct** et varie sur cache froid, alors que `parcel_residuel.sdp_residuelle_m2` (RUN
   SERVI) est stable à 26. Le rapport lit désormais la **valeur du run servi** → PDF = écran = fiche.
3. **Phrase de classement DÉRIVÉE DES RÈGLES.** `_contrainte_limitante` compare les mesures aux règles et
   nomme la règle qui mord, chiffrée : BZ1065 → « la hauteur limite : le bâti existant atteint un faîtage
   mesuré de 10,3 m pour 7 m autorisés — pas de marge en surélévation. » (plus de contradiction avec le
   tableau : l'emprise à 12 % n'est PAS la contrainte, la hauteur l'est). Si aucune ne mord, c'est dit.
4. **Risques : une ligne PAR ALÉA, sans doublon DEAL/PPR.** Les entrées Géorisques « Aléa X » et les
   entrées « PPR — zone rouge/bleue » du même aléa FUSIONNENT : CX0800 passe de 4 lignes à 2 (Inondation,
   Mouvement de terrain), chacune avec niveau (Fort), **zone PPR + part** (Zone rouge · 23 %) et implication.
5. **Parcelle nue : tableau des 8 ventes de TERRAIN NU** (`marche_service.comparateur_terrain`, via
   `dvf_mutations_parcelle`, même format que le bâti : date · surface · prix · €/m² · distance). La page 1
   de CX0800 n'est plus à moitié vide.
6. **Badge de fiabilité recalibré sur ESTIMATION-BANC-1** (écart médian mesuré par segment : appartement
   17 %, maison 32 %, terrain nu 19 %). « Élevée » < 15 %, « Moyenne » < 25 %, « Limitée » au-delà → maison
   **Limitée**, terrain **Moyenne**. La note affiche « Précision mesurée sur les ventes 2025 : ±32 % ».
   Même règle à l'écran.
7. **Titre sans adresse** : « Parcelle CX0800 · Saint-Leu » (plus la commune seule).
8. **Parcelle bâtie : lecture FONCIÈRE** à côté de la lecture bâti (comme la variante lien) — surface de la
   parcelle × repère terrain nu = valeur foncière (€, arrondie), avec la part du bâti : BZ1065 = 600 000 €,
   soit 86 % de l'ordre de grandeur bâti.

## Garde légal (test §2 `test_aucune_requete_portail_dans_le_depot`)

Rouge sur 3 chaînes d'affichage ANNONCE-3/5 (sous-titre « Annonce Leboncoin » du PDF, 2 phrases d'échec de
la route lien). Remis VERT par **allowlist LIGNE PAR LIGNE** dans `tests/test_pige_socle.py`
(`_ALLOWLIST_LIGNES`), uniquement des chaînes d'affichage — aucun fichier entier, aucun appel réseau.

## Recette (routes réelles, run q_v20)

`pdf/recette-{BZ1065,CX0800,lapossession}.pdf` régénérés : **2 / 2 / 1 pages** · HTTP 200 · **outil == Docs**
(md5 pdftotext identique) · **PDF == écran** (`/radar/annonce/estimation/BZ1065` → médiane 3528, fiab
limitee, précision 32, ordre de grandeur 695 000 €, foncière 600 000 € / 86 % — identiques au PDF).
Capture `png/ecran-parcelle-fix-accordeon.png` (ordre de grandeur + lecture foncière + accordéon ouvert).

## Vérifications

`tsc -b` 0 · `vitest` **301/301** · `pytest` famille hook **2710 passed, 0 failed** (dont `test_annonce_pdf`
**15/15** mis à jour, `test_pige_socle` vert, verrou de graphe 4/4).
