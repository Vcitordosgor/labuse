# FICHE-FIX-4 — retouches de recette de la fiche (captures Vic du 27/09)

**Branche** `feat/fiche-fix-3` · worktree `~/Desktop/labuse-kelfix` · ports 8545/5745 · Opus · 2026-09-28.
**Maquette de référence** `docs/audit-2026-09/fiche-fix-3/maquette-v3.html`.
**Base** : suite de KELFONCIER-FIX-2 (Partie B), avec `git merge origin/main` en cours de route
(SOURCES-FIX-1 : SCOT/§Urbanisme + EnR-APER/mesures compensatoires/§Risques — passés en forme `Ligne`).

Un lot = un commit, captures avant/après sous `captures/fiche-fix-4/`. Témoins :
`97415000AB0134` (AU, nu) · `97411000BZ1065` (St-Denis) · `97402000AB1117` (PP) ·
`97411000DE0231` (bâti) · `97418000AC0198` (Sainte-Suzanne, zone A).

`tsc` **0** · `vitest` **223** (218 + 5 format) à chaque lot.

---

## Lots

| Lot | Section(s) | Commit | Ce qui change |
|-----|-----------|--------|---------------|
| **A** | En-tête + carte | `4f5fa71c` | A1 carte d'en-tête FLOTTANTE (marge haute `pt-2.5`, coins arrondis 4 côtés, sans liseré au défilement). A2 sélection : `offset:[-200,0]` sur le vol quand la fiche est ouverte → parcelle centrée dans la zone visible, pas sous le panneau ; liseré blanc `parcels-sel` (#ECF5EF) intact. |
| **B** | Format partagé | `d5b48190` | `lib/format` : `fmtDateSirene` (1900→« n.c. »), `anneeSirene`. `formes` : la VALEUR d'une Ligne ne se coupe plus (nowrap ; retour à la ligne seulement entre libellé et valeur) ; libellé/sous-ligne de Tuile tronqués « … » + `title`. Test `format.test.ts` (5 cas). |
| **C** | Identité | `0785f7f9` | Historique en Frise (1 segment même sans changement) ; 3 paragraphes gris → « i » ; détention en Ligne ; Scan patrimoine en bouton ; filiation en Ligne (date JJ/MM/AAAA) ; lignes « proprio » doublons retirées. |
| **D** | Terrain | `91d44201` | Profil altimétrique OUVERT par défaut, parcelle seule, sans « Tracer un autre profil ». |
| **E** | Bâti | `5a339995` | Une ligne de comptes « N bâtiments BD TOPO · N RNB · N adr. BAN » ; nature du toit + détails dans un Repli « détail du bâti » ; décimales à la virgule (faîtage/égout/BD TOPO) ; établissements visibles (DE0231 : 14). |
| **F** | Urbanisme | `53abceac` | Verdict complet toutes zones (« N destinations interdites · N sous condition ») ; zones non indexées → 6 tuiles grises « non calibré » ; PLU en Ligne (JJ/MM/AAAA + badge document) ; SCOT en Ligne ; Annuaire/Vérif procédure en boutons. |
| **G** | Risques | `c527f6a3` | Verdict lisible (aléa dominant + CASIAS) ; barre « N couches » retirée ; SIS/CASIAS/EnR/mesures compensatoires en Lignes de vigilance (« i ») ; CatNat en Repli « N arrêtés · dernier JJ/MM/AAAA » ; Pièges & risques en bouton. |
| **H** | Réseaux | `c47fdcd3` | Sous les cases-état, toute la desserte en Lignes (fibre FttH·op., arrêt/ligne/pôle, TCSP, trafic, axe, raccordement) ; paragraphes en « i ». Gestionnaires + Viabilisation conservés. |
| **I** | Fiscalité | `607be1fd` | 4 tuiles (foncière·aménagement·zonage A/B/C·TVA) ; Pastilles allumées ET éteintes (ZFANG/FRR/ORT · QPV/PVD/Cœur de ville) ; doublons retirés (FiscalLeviers, taux) ; dispositifs en Repli ; taxe en bouton ; disclaimer en source. |
| **J** | Marché | `2fa4aa40` | Tuiles des seuls types servis ; verdict qui ne cite que des valeurs présentes en tuile ; prix de sortie/valeur/loyers/acquéreur PM en Lignes (« i ») ; outils 2×2. |
| **K** | Quartier | `f9628ae9` | Verdict utile (secteur + niveau de vie + pauvreté + commerces) ; Proximité en 3 tuiles ; quartier INSEE en tuiles 2 colonnes ; libellés de boutons courts. |
| **L** | Potentiel + Simulation | `8b386182` | UN seul verdict ; non constructible → rouge + tuile SDP + ligne « pourquoi » + boutons Densifier/Gabarit, panneau Faisabilité replié sous « Étudier quand même » ; constructible → panneau ouvert. Simulation : paragraphe en « i », 3 boutons conservés. |
| **M** | Recette des boutons | ce commit | Tableau ci-dessous. **Aucun bouton cassé.** |

### Contrainte respectée
`constructibilite.tsx` (fichiers de **FaisabiliteTab / BilanTab**, FAISABILITE-POLISH-1 en attente de
merge) n'est **pas modifié** : DispositifsBody, RtaaFromBilan, TaxeAmenagementBlock, FaisabiliteTab,
BilanTab sont pilotés/repliés au point d'appel (Fiche.tsx), jamais édités.

---

## Lot M — recette des boutons (5 témoins)

Chaque bouton d'outil (`data-porte`) ouvert dans sa section, cliqué, état du store lu, puis remis à
zéro (script `scripts/kelfix-recette-boutons.mjs`). Toutes les cibles de `setModule` sont des modules
réels (ModulePanel `registry` : programme→M22, plu→Plu, patrimoine→ScanPatrimoine, permis→M03,
temps→M08, courriers→M09, risques→Risques, taxe-amenagement→TaxeAmenagement,
calculette-fonciere→CalculetteFonciere, assemblage→M16, comparer→CompareModule).

| Section | Bouton (data-porte) | Action attendue | Constaté (AB0134/AB1117/DE0231) |
|---------|--------------------|-----------------|-----------|
| Identité | Scan patrimoine (`patrimoine`) | module=patrimoine | ✅ (PM) · absent si PP (correct) |
| Identité | Courrier SPF (`spf-letter`) | module=courriers | ✅ (PP) · absent si PM (correct) |
| Urbanisme | Annuaire PLU (`annuaire`) | module=plu | ✅ |
| Urbanisme | Vérif procédure (`verif-procedure`) | module=plu | ✅ |
| Urbanisme | Simuler l'ouverture (`simuler-ouverture`) | module=plu | ✅ (zones AU) |
| Risques | Pièges & risques (`risques`) | module=risques | ✅ |
| Fiscalité | Taxe d'aménagement (`taxe-amenagement-outil`) | module=taxe-amenagement | ✅ |
| Marché | Marché commune (`marche`) | contexte commune | ✅ contexte=commune |
| Marché | Priorité · section (`secteur-opp`) | filtres + carte | ✅ (map, module=∅ attendu) |
| Marché | Comparer (`comparer`) | comparateur ouvert | ✅ module=comparer |
| Marché | Remonter le temps (`temps`) | module=temps | ✅ |
| Quartier | Permis commune (`permis`) | module=permis | ✅ |
| Quartier | Fiche commune (`fiche-commune`) | contexte commune | ✅ contexte=commune |
| Potentiel | Densifier l'existant (`densifier-filtre`) | filtres ouverts | ✅ (filtres, module=∅ attendu) |
| Potentiel | Ouvrir le Gabarit (`gabarit`) | module=programme | ✅ |
| Simulation | Faisabilité (`faisabilite-outil`) | module=programme | ✅ |
| Simulation | Calculette (`calculette`) | module=calculette-fonciere | ✅ |
| Simulation | Assemblage (`assemblage-outil`) | module=assemblage | ✅ |

**Résultat : 18/18 boutons répondent correctement, sur les 3 profils testés (PM, PP, constructible).**
Les deux `module=∅` (Priorité·section, Densifier) sont le comportement voulu (navigation carte /
ouverture du panneau Filtre, pas un module). La présence complémentaire Scan patrimoine (PM) ↔
Courrier SPF (PP) est correcte. Aucun correctif nécessaire.

---

## Formats unifiés (Lot B, appliqués Lots C–L)

- **Décimales à la virgule** (`fmtDec`) : faîtage « 18,5 m », égout, BD TOPO, azimut « 3,8° ».
- **Dates JJ/MM/AAAA** (`fmtDateNum`) : filiation « 08/12/1989 », PLU « 26/11/2025 », CatNat
  « 20/03/2025 », acquéreur PM « 27/05/2025 », ORT.
- **Année SIRENE 1900 = « n.c. »** (`anneeSirene`) sur la tuile « Créée · état » d'Identité.
- **Nombres jamais coupés** : valeur d'une `Ligne` en `white-space:nowrap` (fin du « 17 515 € »
  caractère par caractère) ; le seul retour à la ligne est entre libellé et valeur.
- **Sous-lignes tronquées** « … » + `title` (Terrain › Exposition « versant (RGE ALTI, fenêtre
  200 m) »).

## Écarts assumés

1. `constructibilite.tsx` intouché (contrainte POLISH-1) : DispositifsBody / RtaaFromBilan / la
   Situation `<Line>` restent tels quels ; TaxeAmenagementBlock lu dans le Repli Fiscalité.
2. Quartier : MarcheSecteurBlock (secteur) et AutourZoneBlock (isochrone) conservés (composants
   dédiés, déjà compacts) — non reconvertis en tuiles.
3. Réseaux : GestionnairesBlock garde ses rangées compactes (pas de champ « échéance MM/AAAA » servi).
4. Captures carte (Lot A2) : le WebGL headless ne rastérise pas le zoom de façon fiable ; le vol +
   liseré sont vérifiés par le code (effet unique partagé par toutes les entrées de sélection).
