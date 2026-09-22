# MANDAT GABARIT-1 — Gabarit réglementaire (moteur + outil)

Date : 22/09/2026 · Modèle : Claude Code Fable (le lot A0 demande des rapprochements sur tout le code)
Branche : `feat/gabarit-1` depuis `origin/main` à jour
Worktree : `git worktree add ~/Desktop/labuse-gabarit -b feat/gabarit-1 origin/main`
Ports de session : API **8125** · Vite **5325** · `LABUSE_API_DEV` pointé dessus · `statement_timeout` posé
Cahier des charges : `docs/GABARIT/CDC-GABARIT.md` (texte de Vic — fait foi sur le fond : principe absolu, contrat, terminologie, panneau, tests)
Ce mandat fait foi sur la méthode et sur ce qui est réel vs fictif.
Livrables : `docs/GABARIT/A0-RAPPORT.md`, `docs/GABARIT/RAPPORT-GABARIT-1.md`, `docs/GABARIT/captures/`

---

## Étape 0 — avant toute écriture

`pwd` = `~/Desktop/labuse-gabarit` · branche `feat/gabarit-1` · `git status` propre · `.env` copié depuis `~/Desktop/labuse` · rien sur 8125/5325.
Sinon : STOP, signaler, ne rien écrire.
Jamais de merge. Jamais de `residuel-serve`. Jamais de redémarrage de l'API en boucle (base partagée). Un commit par lot.

---

## Pourquoi ce n'est pas un simple mock

Le CDC prévoit une parcelle fictive. Or trois familles sur quatre existent déjà en réel et sourcé dans LABUSE :

- **Règles chiffrées PLU** : `config/plu_destinations/974*.yaml`, bloc `regles` (retraits voie / limites dont `forme: alignement`, hauteur, CES, pleine terre — 1 919 règles validées avec citation), lues par `faisabilite/zonage.py`, validées-only, verrou V6a.
- **Géométries** : 431 k parcelles cadastrales, parcelles voisines, BD TOPO (routes).
- **Risques** : Géorisques / aléas / PPR ingérés (à qualifier en A0 : réglementaire ou informatif).

**Règle du mandat : réel partout où la donnée existe, est sourcée et passe la mesure. Le fictif ne vit que dans les fixtures de test.** Le moteur ne fait pas la différence (même contrat).

Deux adaptations du CDC, à appliquer :

1. **Moteur en Python côté back**, pas en TS/Turf. Doctrine LABUSE : zéro recalcul au front, tout chiffre servi par l'API et porté par le registre (verrou V5f). Le contrat TS du CDC devient le contrat JSON de l'endpoint (modèles pydantic `GabaritInput` / `GabaritResult`), géométrie via shapely/PostGIS déjà en place. Le front affiche, il ne calcule rien.
2. **Point de raccordement unique** = un builder `build_gabarit_input(idu)` qui assemble cadastre + `zonage.py` + risques + classification des limites. C'est LE seul endroit où les vraies données entrent. `compute_gabarit(input)` reste pur et déterministe.

---

## Lot A0 — inventaire et mesure (lecture seule, commit doc)

Répondre avec preuve `fichier:ligne` :

1. **Prototype** : un Gabarit / enveloppe / extrusion existe-t-il déjà (grep) ? Si oui, on le fait évoluer, pas de second outil.
2. **Stack** : lib carte, bascule 3D existante (extrusion bâtiments de RECETTE-6 — réutiliser le même bouton), utilitaires géo existants (assiette clippée de SCORING-6 lot A, anneau 0,5 m d'Assemblage, buffers). Turf n'est PAS à ajouter.
3. **Règles** : pour une zone, comment `zonage.py` rend retraits voie / limites (forme alignement, `min_m`), hauteur (faîtage et égout — le faîtage sert à l'extrusion, l'égout est affiché s'il existe, nommé), CES ; ce qu'il rend quand une feuille est `propose` ou absente → le Gabarit lit ces valeurs **par `zonage.py`**, jamais une copie. Un `propose` = bloquant.
4. **Risques** : quelles tables portent un zonage **réglementaire** (PPRN / PPRI / PPRL, zones rouge/bleu avec règlement) et lesquelles un aléa informatif. Seul le réglementaire peut devenir une exclusion ; un aléa n'exclut rien. Même question pour les SUP. Si rien de réglementaire n'est en base : famille Risques = `not_integrated`, sourcée, jamais « intégrée » par défaut (CDC §3).
5. **Classification des limites — le point dur, rien n'existe.** Mesurer sur 30 parcelles U tirées au sort (3 communes, dont 97410000AN0347) une méthode simple :
   - segment du contour touchant une parcelle voisine à ≤ 0,5 m → limite séparative ;
   - segment sans voisin cadastré ET à ≤ N m d'un tronçon BD TOPO → voie ;
   - sans voisin et sans route (ravine, domaine public non routier) → **non classée = bloquant** ;
   - `side` vs `rear` : `rear` = séparative sans point commun avec un segment voie.
   Livrer : une capture par parcelle (segments colorés sur ortho), taux juste / faux / non classé. **Seuil pour servir : 0 faux sur 30.** « Non classée » est acceptable — elle bloque honnêtement. La classification servie porte sa propre source (`provider: LABUSE — adjacence cadastre + BD TOPO <millésime>`) : c'est une mesure, pas une supposition.
6. **Registre** : ids existants (surface parcelle, hauteur PLU, CES) ; ids à créer (zone d'implantation m², plafond d'emprise m², couverture). V5f doit rester vert.
7. **Multi-zones** : parcelle à cheval sur ≥ 2 zones PLU (9,9 %) → pour GABARIT-1, bloquant (règle non unique), pas de découpage.

**Sortie A0** : `A0-RAPPORT.md` avec un tableau de décision par famille et par fait : **Réel / Fictif-tests / Bloquant**.
CC poursuit sans attendre. **STOP seulement si la classification échoue au seuil** : dans ce cas les lots A–C sont livrés quand même, l'outil s'ouvre derrière un flag admin sur des fixtures, et la classification devient GABARIT-2.

---

## Lot A — moteur

`src/labuse/gabarit/` : `contract.py` (pydantic, CDC §2) · `validate.py` (CDC §3, toutes les vérifications, message exact « Calcul incomplet — donnée réglementaire manquante ») · `engine.py` (CDC §4 : reculs par type, soustraction des exclusions, zone finale Polygon/MultiPolygon/vide, surface, plafond = `areaM2 × percent / 100` calculé À PART, jamais de `min()`) · `builder.py` (raccordement unique) · endpoint `GET /api/outils/gabarit/{idu}`.
Le résultat expose : règles appliquées (groupées par `ruleId` + valeur + source, jamais fusionnées si valeur ou source diffère), règles non intégrées, couverture (4 familles), géométries pour la carte, hauteur sourcée.
Aucun champ estimatif dans le résultat — liste noire testée : logements, étages, sdp, coût, valeur, potentiel.

---

## Lot B — outil « Gabarit réglementaire »

- 18e entrée du menu Outils (outil séparé — pas de refonte de Faisabilité). Omnibox IDU / adresse / référence courte comme partout + « ou cliquez la carte ».
- Panneau 320 px (pas de table large) : les 4 chiffres, couverture 4 familles, « Voir les règles appliquées », règles non intégrées avec compteur. Terminologie CDC §5, formulations interdites retirées.
- Carte : contour cadastral, retraits, exclusions, zone d'implantation réglementaire — couleur franchement distincte du fond (jamais de camaïeu vert), légende « Zone d'implantation réglementaire ». Couches affichées seulement après validation réussie.
- 3D sur le bouton 3D existant : extrusion de la seule zone calculée à la hauteur sourcée, titre « Enveloppe réglementaire selon les règles intégrées », indisponible si calcul incomplet.
- Ponts : tuile depuis Étudier un bien et depuis Faisabilité, fil de retour `<RetourOutil/>` ; Gabarit renvoie vers Faisabilité.
- DA existante : tokens, survol vert opaque, état actif vert opaque, aucune infobulle, aucun scroll horizontal, aucun redesign.

---

## Lot C — tests et recette

- `tests/gabarit/` : les 20 cas du CDC §10 sur fixtures fictives (contrat identique au réel) + test « feuille `propose` → bloqué » + test liste noire.
- `pytest` ciblé puis suite complète · `tsc` · build front.
- Recette navigateur (Playwright MCP) des 4 parcours du CDC : Générer · Voir les règles · 2D/3D · Réinitialiser — sur 97410000AN0347, une parcelle bloquée (limite non classée ou multi-zones), une parcelle en zone PPR rouge si réel. Captures avant/après dans `docs/GABARIT/captures/`. Un point n'est « fait » qu'avec capture.

---

## Hors mandat

Tiroir fiche parcelle (§10 Potentiel) et exports (Flash, Dossier) → **GABARIT-2**, après recette de celui-ci · classification si échec A0 → GABARIT-2 · refonte de Faisabilité · toute règle non chiffrable (H/2, bandes de constructibilité, alignements imposés) = `not_integrated`, jamais approchée · merge · `residuel-serve`.

---

## Rapport final

`RAPPORT-GABARIT-1.md` selon CDC §12 (architecture identifiée, fichiers, contrat final, fonctionnement du moteur, règles réelles servies, règles non intégrées, emplacement exact du builder, commandes et résultat de chaque validation) + tableau Réel / Fictif-tests / Bloquant final + arbitrages pris par CC. Dernier commit = rapport.
