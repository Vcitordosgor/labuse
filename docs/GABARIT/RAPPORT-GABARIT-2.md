# RAPPORT GABARIT-2 — Classification des limites v2 et passage au réel

Branche `feat/gabarit-2` (depuis `feat/gabarit-1`, base non mergée), worktree `~/Desktop/labuse-gabarit`,
ports API 8125 / Vite 5325. 6 commits (A→E + rapport), **aucun merge**, aucun `residuel-serve`,
suite pytest complète laissée à Vic. Références : `docs/GABARIT/CDC-GABARIT.md`, `A0-RAPPORT.md`,
`A0-2-MESURE.md`.

## Ce qui change depuis GABARIT-1

GABARIT-1 servait le moteur sur fixtures (la classification des limites échouait la mesure).
GABARIT-2 **fait passer l'outil au réel** : la classification voie/séparative par arête est
reconstruite (route d'abord), **mesurée 0 faux/70**, puis **servie**. L'outil est désormais un vrai
18e outil du menu, et une ligne « Gabarit réglementaire » apparaît dans la fiche parcelle (§10).

## 1. Classification v2 — `src/labuse/gabarit/limites.py`

Cœur PUR `classify_edges` (géométries en entrée, EPSG:2975, aucune DB) + `summarize_edges`
(verdict parcelle) + couche `classify_parcel_limits` (requêtes PostGIS). Par **tronçon de 3 m**
(contour densifié, classé par son **milieu** — supprime l'artefact de coin où un segment ne touche un
voisin qu'à son sommet, qui masquait les façades en A0) :

1. voisin collé **parcelle de voirie** (axe BD TOPO traversant + sans bâti) → **VOIE** ;
2. axe carrossable **dans l'emprise** de l'arête (≤ `largeur/2`) → **VOIE**, même avec voisin collé
   (la rue longe la limite partagée — centre-ville) ;
3. voisin cadastré réel collé (≤ 0,5 m) → **SÉPARATIVE** (une route *derrière* un voisin ne fait pas
   façade — pas de faux-voie sur parcelle intérieure) ;
4. arête ouverte à portée façade (≤ `largeur/2 + 3,5 m`) → **VOIE** ;
5. sinon → **NON CLASSÉE** (motif nommé). `rear` = séparative sans sommet commun avec une voie ;
   aucune voie → « parcelle sans façade sur voie » (enclave/drapeau).

Tronçons = `spatial_layers kind='voirie'` hors Sentier/Escalier ; `largeur` = attribut BD TOPO (défaut 4 m).

## 2. Mesure — 70 parcelles (`A0-2-MESURE.md`, `scripts/gabarit_a0_2_mesure.py`)

Échantillon adversarial (31 d'A0 dont les 20 échecs + 20 centre-ville + 10 drapeau/enclave + 9 périurbain).

| Issue | n | Lecture |
|---|---|---|
| **Servie** (≥ 1 façade, limites classées) | **42** | frontage détecté, séparatives/fond tranchés |
| Bloquée — sans façade (enclave/drapeau) | 15 | périmètre **100 % clos** par voisins (mesuré) |
| Bloquée — limites non qualifiées | 13 | littoral (AN0347) / ravine / gap, ou arête à la marge du seuil |
| **FAUX** | **0** | audit auto : 0 faux-voie, 0 faux-sep sur les 42 servies |

**Audit automatique** (preuve, pas à l'œil seul) : sur les 42 servies, aucune arête « voie » sans route
réelle (≤ 8 m) ni parcelle-voirie, aucune « séparative » à une route sans voisin ; les 15 « sans façade »
sont 100 % closes ; les blocs « non qualifiées » à la marge ne servent aucun chiffre (aucune donnée
fausse). **Seuil 0 faux / 70 ATTEINT** → service autorisé. « Faux » = parcelle qui *sert* une
classification fausse : il y en a 0 ; à la marge, l'outil **refuse** plutôt que de deviner (fiabilité
d'abord). Le taux de blocage (28/70) est un **majorant** (échantillon sur-pondéré en enclaves/littoral).

## 3. Ce qui est servi (réel) et ce qui bloque

**Servi** (parcelle avec PLU calibré + limites classées) : surface (cadastre), zone d'implantation
(parcelle − reculs par arête − exclusions), plafond d'emprise (surface × CES/100, à part), hauteur
faîtage, 4 familles de couverture, règles appliquées groupées avec source, exclusion PPR rouge
géométrique. Exemples recette : IE0153 805/394/483/13 m, HD0281 2387/1200/1194/10 m (+ PPR rouge exclu).

**Bloque, motif métier** (« Calcul incomplet — donnée réglementaire manquante » + raison) : PLU non
validé / `propose` / non calibré (ex. zone N) ; emprise (CES) non réglementée ; parcelle à cheval sur
≥ 2 zones ; parcelle sans façade sur voie (enclave) ; limites non qualifiées (littoral, ravine, gap).

## 4. Fichiers créés / modifiés

Back : `src/labuse/gabarit/limites.py` (créé) ; `builder.py` (branche limites + PPR rouge géométrique +
millésime BD TOPO depuis `data_sources`) ; `api/gabarit.py` (docstring) ; `registre/donnees.py`
(id réel). Front : `components/fiche/GabaritLine.tsx` (créé, tiroir §10 + mini-plan SVG) ;
`fiche/Fiche.tsx` (insertion §10) ; `outils/Gabarit.tsx` (démo retirée, légende enrichie) ;
`outils/registry.ts` (`hidden` retiré → 18e outil visible). Tests : `tests/gabarit/test_limites.py`
(créé) ; `test_builder.py` (MAJ GABARIT-2). Mesure : `scripts/gabarit_a0_2_mesure.py` (créé, 70 captures).

## 5. Raccordement (où entre le réel)

`build_gabarit_input(session, idu)` reste le **point unique**. Chaque limite servie porte
`source.provider = "LABUSE — adjacence cadastre + BD TOPO <millésime>"`, `document = BD TOPO® —
troncon_de_route`, `versionDate = <millésime>` — **millésime lu dans `data_sources`, jamais codé en
dur** (`BD TOPO® V3 (IGN) — édition non enregistrée`). Le recul appliqué et son article PLU figurent
dans le détail de la règle (arbitrage §7). Exclusions = `ST_Intersection(parcelle, ppr INTERDICTION)`.

## 6. Commandes de validation et résultats

| Contrôle | Commande | Résultat |
|---|---|---|
| Mesure 70 | `gabarit_a0_2_mesure.py --sample` | 42 servies / 28 bloquées / **0 faux** |
| Tests | `pytest tests/gabarit/` | **42 passés** (engine 20+ · builder · limites 11) |
| Registre | `registre.verifier()` | **0 erreur** |
| Verrou V5f | `verrou_outils_registre` | **vert — 18 outils** mappés |
| Types front | `tsc -b` | **0 erreur** |
| Build front | `vite build` | **OK** |
| Lint | `ruff check` | **All checks passed** |
| Recette | Playwright, API 8125 / front 5325 | 5 parcelles + tiroir fiche (§7) |

## 7. Recette navigateur (`captures/gabarit-2/recette-*`)

1. **IE0153** (centre-ville Saint-Denis) — servie 805/394/483/13 m, 4 familles, 3 non intégrées ;
   règles appliquées : reculs **BD TOPO® V3 (IGN)**, emprise/hauteur **PLU Saint-Denis Uj**.
2. **HD0281** — servie + **exclusion PPR rouge** dessinée (rouge, soustraite de la zone) ; **3D** =
   extrusion de la seule zone à la **hauteur sourcée 10 m** (vérifié par introspection du style ;
   canvas WebGL non capturable en headless, limite connue).
3. **CP1097** (Saint-Paul) — « Calcul incomplet » + « emprise (CES) non réglementée / non validée ».
4. **CH0196** — « parcelle sans façade sur voie (enclave ou accès en drapeau) ».
5. **DZ0053** — « parcelle à cheval sur ≥ 2 zones PLU (règle non unique) ».
6. **Tiroir fiche §10** (IE0153) : 4 chiffres + **hauteur citée « §4 Urbanisme »** + **mini-plan 2D
   SVG** (zone/retraits/contour) ; « Ouvrir le Gabarit → » ouvre l'outil pré-rempli avec un fil de
   retour **« ← Fiche »** qui referme l'outil sur la fiche.

## 8. Arbitrages CC

1. **Marge route `+3,5 m`** (mandat : `+1,5`) : l'axe BD TOPO est souvent à demi-chaussée +
   trottoir/accotement (~4-5 m ; IE0153 à 4,4 m). `+1,5` ratait ces façades ; `+3,5` les capte, audit
   0 faux. Discriminateur `≤ largeur/2` (sur la chaussée) pour distinguer « rue le long de la limite »
   (voie) de « route derrière un voisin » (séparative).
2. **Densification 3 m + test au milieu** : supprime l'artefact de coin (segment touchant un voisin
   seulement au sommet) — non prévu par le mandat, nécessaire pour ne pas masquer les façades.
3. **Source de la limite** : `provider`/`document`/`versionDate` = BD TOPO (mandat, millésime
   `data_sources`) ; le recul (valeur PLU) + l'article figurent dans le **détail** de la règle — la
   valeur reste tracée au PLU sans casser la cohérence source↔règle du validateur.
4. **Blocage conservateur à la marge** : une arête non classée près d'une route (~5 m) bloque plutôt
   que de servir un gabarit incertain (CDC « la fiabilité prime sur la quantité »).
5. **Bouton démo retiré du front** (mandat lot B) groupé avec les autres retouches front (lot C) ;
   endpoint `/outils/gabarit/demo` + fixture **conservés pour les tests**.
6. **Fil de retour fiche** : `pushOutilRetour({module:'', label:'Fiche'})` — `retourOutil` ferme
   l'outil (module vide) en gardant la fiche (`selectedIdu` persistant), faute d'un champ « selectedIdu »
   dans le `restore` du store (non modifié).

## Hors mandat (rappels)

Exports (Flash, Dossier) → GABARIT-3 · règles PLU non chiffrables (H/2, bandes, prospect) =
`not_integrated` · voirie non cadastrée hors BD TOPO · merge · `residuel-serve` · suite pytest
complète (à lancer par Vic).
