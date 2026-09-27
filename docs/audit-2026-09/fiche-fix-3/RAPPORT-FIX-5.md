# FICHE-FIX-5 — deuxième recette de la fiche (captures Vic du 28/09)

**Branche** `feat/fiche-fix-3` · worktree `~/Desktop/labuse-kelfix` · ports 8545/5745 · Opus · 2026-09-28.
**Préalable** : `fix/faisabilite-polish-1` est mergé dans main (`e56432d9`, présent dans la branche) →
`constructibilite.tsx` (FaisabiliteTab/BilanTab) redevient modifiable. Étape 0 bis
`git fetch && git merge origin/main` : rien de nouveau (déjà à jour).

Témoins : `97411000EM0174` (Um, PP, bâti) · `97411000DE0231` · `97415000AB0134` (AU) ·
Sainte-Suzanne `97418000AC0198` (A) · `97410000BZ1065` (→ `97411000BZ1065`).
`tsc` **0** · `vitest` **223** à chaque lot.

## Règle de preuve
Les captures de carte sont faites en navigateur qui **rastérise le WebGL** (Chromium 1217 +
SwiftShader) — `headless:false` a été tenté mais son `page.screenshot` se bloque sans session
d'affichage active. Une capture de carte montre bien la parcelle zoomée et détourée
(`scripts/kelfix-map.mjs`).

## Lots

| Lot | Commit | Résultat |
|-----|--------|----------|
| **A** sélection | `2c5cad2d` | **Cause** : le liseré (parcels-sel/ile-sel) ne s'affiche que si la parcelle est dans la source correspondante ; lien profond / clic hors commune chargée → aucune. **Fix** : source `selection` dédiée alimentée par la GÉOMÉTRIE (getParcelGeojson), `selection-line` blanc remonté au-dessus (m.moveLayer), flyTo sur le centroïde (marge panneau -200px). Liseré + zoom GARANTIS, tous chemins (tous passent par select()/focusParcelle() → cet effet). |
| **B** en-tête | `fc4fb1be` | En-tête collant OPAQUE jusqu'au bord haut (pt-2.5 flottant de FIX-4 retiré, coins hauts carrés) — plus de trou. |
| **C** Identité PP | `0e9e5ebe` | Verdict « Propriétaire non identifié — personne physique ou hors PM », SPF/CERFA en « i », Courrier SPF en bouton, filiation en Ligne, carte fermée = « Particulier ». |
| **D** Terrain | `f84fad1b` | « Détections › Piscine ~14 m² · confiance 0,89 » (méthode en « i ») ; Exposition raccourcie « versant · RGE ALTI ». |
| **E** Urbanisme | `2d80fe69` | Tuiles courtes sans troncature (Hauteur/Emprise/Recul voie/Recul limites/Pleine terre/Stationnement, « 18 m », « 1 / logt », article en sous-ligne) ; SDP consommée en Ligne (plus flottante). |
| **F** Risques | `3a2787d2` | Vigilances (ICPE, SUP, ABF, HT/HTA) en Lignes ambre + « i » ; plus d'encadré (Rappel) ni de puce ▲. |
| **G** Réseaux | `5fec25c9` | Accès, Viabilisation (indices en Repli), Gestionnaires (opérateur · type + confiance), Solaire (badge Estimé), Assainissement → Lignes ; méthode en source/« i ». |
| **H** Marché | `8734fdb5` | Phrases en « i » (secteur vs commune) ; Ventes < 100 m en 2 Lignes ; les 3 boutons → un seul « Outil Communes — <commune> ». |
| **I** Quartier | `f75424e3` | Boutons « Étude de zone · Chalandise » / « · Particulier » (ouverts sur la parcelle) + Permis / Fiche commune ; permis à proximité repliés après 5. |
| **J** Potentiel | `083cdd22` | Panneau replié « Étudier quand même » dès SDP résiduelle = 0 (toute cause) ; Gabarit = vignette pleine largeur + 3 Lignes nowrap, un seul « Ouvrir le Gabarit ». |

## Lot A — chemins de sélection (× effet unique)

Tous les chemins ci-dessous appellent `select(idu)` ou `focusParcelle(idu)` → le MÊME effet MapView
(source `selection` + flyTo). Vérifié en capture pour clic carte + lien profond ; les autres passent
par le même point d'entrée.

| Chemin | Entrée | Zoom + liseré |
|--------|--------|---------------|
| Clic carte | `select(idu)` | ✅ (map-A-click : DH0004 détourée, zoomée) |
| Lien profond `#idu=` | `select(idu)` | ✅ (map-A-storeSel : DE0231 détourée) |
| Omnibox / résultats / liste filtre | `select(idu)` | ✅ même effet |
| Projets / CRM / Scan / Comparer / Assemblage | `select(idu)` | ✅ même effet |
| Pièges (lot) / Veille / Radar (annonce) | `select(idu)` | ✅ même effet |
| Précédent / suivant / fiche commune→parcelle | `select(idu)` | ✅ même effet |

## Lot K — cohérence fiche ↔ outils (recette des boutons)

`scripts/kelfix-recette-boutons.mjs` : chaque bouton ouvre le bon module sur la parcelle/commune.

| Bouton (data-porte) | Ouvre | Constaté |
|---------------------|-------|----------|
| Scan patrimoine (`patrimoine`) | ScanPatrimoine | ✅ (PM) |
| Courrier SPF (`spf-letter`) | Courrier | ✅ (PP) |
| Annuaire / Vérif procédure / Simuler (`plu`) | Plu | ✅ |
| Pièges & risques (`risques`) | Risques | ✅ |
| Taxe d'aménagement (`taxe-amenagement-outil`) | TaxeAmenagement | ✅ |
| **Outil Communes (`communes`)** | Communes | ✅ (nouveau, Lot H) |
| **Étude de zone · Chalandise/Particulier (`etude-*`)** | EtudeZone | ✅ (nouveau, Lot I) |
| Permis commune (`permis`) | M03 | ✅ |
| Fiche commune (`fiche-commune`) | contexte commune | ✅ |
| Densifier (`densifier-filtre`) | panneau Filtre | ✅ |
| Ouvrir le Gabarit (`gabarit`) | M22 | ✅ |
| Faisabilité / Calculette / Assemblage | M22 / Calculette / M16 | ✅ |

**17/17 boutons ouvrent le bon outil sur la parcelle/commune. Aucun bouton cassé.**

## Écarts assumés / restes documentés

1. **Isochrone Quartier** (« À pied 15 min / Voiture 5 min ») pas encore aligné sur les rayons km de
   l'outil Étude de zone — refonte d'AutourZoneBlock, non faite (Lot I).
2. **Lot J, dans FaisabiliteTab/BilanTab** (constructibilite.tsx) : items non faits (budget) —
   « Ce que le PLU permet » → repli ; retrait des boutons Comparer / Écrire au propriétaire ;
   « Potentiel de transformation » en Ligne ; Simulation bilan en 3 Lignes + replis. Le repli du
   panneau (item 1) et le Gabarit (item 4) SONT faits. Cas terrain-exigu (résiduel PLU > 0 mais non
   bâtissable) : panneau laissé ouvert.
3. **Lot E, DispositifsBody/RtaaFromBilan** : RTAA/DPU/PEB/SUP encore en paragraphes (les 6 tuiles de
   règles + SDP consommée sont faits).
4. **Captures carte** : rastérisées en headless SwiftShader (visible impossible sans session d'écran).
