# RAPPORT M55-F — cohérence Révélation ↔ résultats + parcours final

Branche `feat/m55-f-parcours` (base `main` c6ae2af0, **stage 9 ter + ajustements mergés —
précondition vérifiée**). Un commit par point. tsc 0, vitest 32/32, build vert. Front seul +
mesure (lecture) — aucun changement moteur ni endpoint de scoring.

## Point 1 — un seul récit de chiffres (commit 60b4f8a9)
**Mesure (reproduite, Saint-Paul + surface≥2000, analyse ON)** — trois requêtes, trois nombres :
| Surface | Source | Résultat |
|---|---|---|
| Révélation | `getFiltre({...filters, analyseLabuse:true})` | 703 retenues, ventilation SQL |
| ResultsSection ventilation | `getStats(ile?scopeOnly:undefined)` | **décorrélé** — scopeOnly retire le tier ; en mode commune `getStats(undefined)`=EMPTY_FILTERS **ignore tout** → 118·1038·2964 (l'univers, = les chiffres de l'accueil) |
| EntonnoirLine « analysées → opportunités » | même source décorrélée | « 431 663 → 98 » |

**Raccord** : ResultsSection dérive désormais du **même `getFiltre(filters,0)`** que la Révélation
et le compteur vivant (stage 8) — ventilation, total, opportunités, détail dossiers, tout d'un
seul appel `uni`. `scopeOnly`/`filteredStats`/`getStats` supprimés. **Prouvé** : un seul `/filtre`
distinct servi ; Révélation « 703 — 0·17·276 » == ResultsSection « 0·17·276 » == entonnoir
« 703 → 17 ».

## Point 2 — la phrase des écartées, chaque nombre se retrouve (commit b8b7a1d9)
« LABUSE a analysé les **9 822** parcelles de Saint-Paul. Selon vos critères (…) : **703 retenues**
— dont 0 brûlante, 17 chaudes, 276 en potentiel long terme, 268 à creuser, 142 déclassées — et
**9 119 écartées par l'analyse** (domaine public, inconstructibles…) *voir pourquoi*. »
- **L'arithmétique boucle (prouvé)** : ventilation 0+17+276+268+142 = **703** = retenues ; retenues
  703 + écartées 9 119 = **9 822** = analysé.
- L'intro porte la **trame** analysée (nouveau `trameQ` = getFiltre analyse OFF), pas les retenues.
- Ventilation **complète** (à-creuser + déclassées ajoutés — plus jamais « 3/4 expliquées sur N »),
  chaque tier survolable. Écartées = étage 0 (exclusions dures). « voir pourquoi » = Tip doctrine
  (jamais masquées, motif en fiche). Nombre unique (703) préservé — point 1 intact.

## Point 3 — les deux choix en fin de filtres (commit a8de74c5)
Deux boutons, la hiérarchie dit la valeur : **« Les faire analyser par LABUSE → »** (mint plein,
dominant — rituel stage 5 inchangé) et **« Voir les N parcelles »** (sobre — liste + carte en tri
factuel, SANS analyse : `setVerdict(true)` + `analyseLabuse` OFF, le seul geste qui les découple).
Bandeau de résultats rendu **honnête** (« ✓ Analyse LABUSE affichée » vs « Tri factuel — sans
analyse », « Comprendre le classement » masqué en factuel — prouvé). **La carte ne bouge qu'au
geste** : `verdict` reste false pendant le réglage → aucune repeinte (results-panel absent, prouvé).

## Point 4 — étiquettes « #rang » retirées (commit 84e281ce)
Layer symbol `parcels-v-badge` (« #6353 ») retirée + sa bascule de visibilité (0-caller). La
référence cadastrale vit sur la fiche. Liseré brûlantes conservé. Prouvé : `getLayer` → absent.

## Point 5 — « ★ Shortlist du jour » retirée (commit 4a6d3118)
Composant `ShortlistToggle` + usage retirés de ResultsSection (0-caller). Backend `/shortlist` et
`api.getShortlist` **intacts**.

## Point 6 — le tri parle client (commit 6432c873)
Libellés : « classement » → **« Meilleures opportunités »** · « mutation ×N » → **« Plus
susceptibles de se vendre »** · **« Surface »**. Tooltip du badge ×N : « Cette parcelle a N fois
plus de chances de se vendre qu'une parcelle moyenne de l'île — estimation LABUSE d'après les
ventes réelles. » « i » sur la barre TRIER : les deux lunettes (opportunité globale = P × qualité
du terrain ; probabilité de vente seule = ce qui va bouger bientôt). Tous prouvés.

## Non-régression (vert)
5 combinaisons `/filtre` identiques (9822·188·1710·3770·51129) · **rituel 3,01 s** · **synchro
stage 8** (compteur 9822 == bandeau 9822) · vieux lien `tv+smin` 0 erreur, analyse héritée · mobile
(deux boutons) · 0 erreur page. Captures `f2_phrase_ecartees`, `f3_deux_boutons`, `f3_factuel`,
`f6_tri`, `f_mobile`.

CC ne merge jamais.
