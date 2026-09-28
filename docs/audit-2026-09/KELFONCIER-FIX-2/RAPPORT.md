# KELFONCIER-FIX-2 — retouches de recette + intérieur des sections de la fiche

**Branche** `fix/kelfoncier-1` · worktree `~/Desktop/labuse-kelfix` · Opus · 2026-09-27
**Base** merge `origin/main` `367ef2f0` (rattrapage FAISABILITE-3 + VEILLE-AUDIT-2).
**Maquette de référence** `docs/audit-2026-09/fiche-fix-3/maquette-v3.html` (copiée depuis `~/Downloads/maquette-fiche-v3.html`).

---

## 0. État de session — à lire d'abord (honnêteté)

- **Partie A (recette) — TERMINÉE** : les 5 lots A à E sont faits, testés, commités (un commit par lot).
- **Partie B (intérieur des sections) — TERMINÉE** (session 2, navigateur relancé) : les **11 sections
  sont câblées aux 12 formes**, un lot = un commit, captures avant/après des 3 témoins (AB0134,
  BZ1065, AB1117) sous `captures/kelfix-B/`. **0 donnée recalculée dans le front.**
  - **Lot F** `c58ae4a7` — Terrain (Verdict · Tuiles · BarreEmpilée CoSIA) + Bâti (Verdict · Tuiles ·
    Lignes · Repli établissements).
  - **Lot G** `a5181756` — Identité (Verdict · Tuiles×4 · Siège/Groupe) + Urbanisme (Verdict ;
    règles-valeurs → Tuiles dans `ReglementPluBlock`).
  - **Lot H** `16e16688` — Risques (Verdict · aléas → Jauge3) + Réseaux (Verdict · CasesEtat glance).
  - **Lot I** `f6f336a9` — Marché (Verdict · Tuiles c3 · Réglette) + Fiscalité (Verdict · Tuiles ·
    Pastilles) + Quartier (Verdict · OutilsSection).
  - **Lot J** `7323b4fa` — Potentiel (Verdict rouge si construction non autorisée) + Simulation
    (Verdict prix de sortie · OutilsSection).
  - **Décision assumée — le verdict par section n'est PAS servi par le back** (vérifié sur le JSON
    fiche : seuls `marche_synthese` + `analyse_labuse` existent). Chaque `Verdict` **réagence des
    faits déjà servis** (occupation, pente, artif, zone, statut AU, prix, dispositifs…) dans l'idiome
    du front — **aucun nombre/seuil recalculé**. Les blocs riches et interactifs (FaisabiliteTab,
    BilanTab, ProprietaireHistorique, ReglementPluBlock détaillé, dispositifs, permis…) sont
    **conservés** sous les formes ; aucune ligne n'est retirée.
  - **Écarts assumés** : Tableau3 Quartier (zone/commune/île) non forcé (triple non servi — la zone
    est déjà portée par `AutourZoneBlock`) ; les `PorteOutil` riches conservés là où l'`OutilsSection`
    compact perdrait le sous-titre ; profil altimétrique gardé inline (composant interactif).
  - Outil de capture : `scripts/kelfix-capture.mjs` (node Playwright direct — le MCP expire à 5 s sur
    la carte WebGL ; on capture l'élément `.fiche-v6` seul).

**Vérifs globales** : `tsc` **0** · `vitest` **218** · `pytest` ciblé vert par lot. Baseline pytest complète : voir §Tests.

---

## Étape 0 bis — rattrapage `origin/main`

`git merge origin/main` : **aucun conflit** (le rebase de la fiche §10 et du registre attendus par le mandat se sont résolus automatiquement, main ayant mergé FAISABILITE-3 et VEILLE-AUDIT-2). Commit de merge `367ef2f0`. `tsc` 0 · `vitest` 204 · pytest : 1 échec connu (`_CONCEPT_MAP → renouvellement`, cf. Lot E) + 2 échecs **pré-existants** au merge (cf. §Tests).

---

## Partie A — retouches de recette

### Lot A — « Secteur » rentre dans l'en-tête · commit `6136bfff`
**Constat** : la ligne « Secteur : … » était rendue en `.addr` **nu**, sans retrait horizontal, alors que les autres enfants de la carte `.tete-collee` portent chacun leur retrait de 14 px → la ligne débordait à gauche, **contre le bord** de la carte (l'impression « hors carte » de la recette).
**Correctif** : nouvelle classe `.sect-line` (même retrait 14 px que l'adresse, sous elle), libellé gris `--txt-dim` (= maquette `--mut`), nom en clair `--txt-hi` (= maquette `--txt`) via `<b>` — exactement la `.sect` de la maquette. L'adresse perd son padding-bas quand un secteur suit (`.addr-row.has-sect`), le secteur porte la fermeture basse. Rien d'autre ne bouge dans l'en-tête.
**Fichiers** : `Fiche.tsx` (bloc secteur), `styles/index.css` (`.sect-line`, `.has-sect`). **Tests** : `tsc` 0 ; aucune assertion existante sur `data-fiche-secteur`.
**Capture** : non produite (MCP navigateur déconnecté) ; changement CSS/DOM documenté ci-dessus.

### Lot B — Scan patrimoine sans « Courrier » ni « Comparer » · commit `ba2c0edf`
**Constat** : dans M02 (Possession du Scan patrimoine), la barre de **sélection multiple** portait « ✉ Préparer les courriers (N) » et « Comparer (N) → ». Le test `ScanRetraits` existant ne les voyait pas car il ne sélectionnait aucune ligne (barre conditionnée à `sel.size > 0`).
**Correctif** : barre retirée ; la **sélection multiple** (cases `data-scan-parc-sel`) ne servait QU'à ces deux ponts → retirée aussi (plus de case morte — même geste qu'OUTILS-S1 Lot D sur Blocs). Store selectors et imports 0-caller nettoyés (`setCourrierPrefillIdus`, `addToCompare`, `openCompare`, `pushOutilRetour`, `Case`, état `sel`). Composants Courrier/Comparateur et endpoints **intacts**.
**Fichiers** : `ModulePanel.tsx` (M02). **Tests** : `ScanRetraits.test.tsx` étendu — `data-scan-comparer`, `data-scan-parc-sel` absents, pas de « comparer » ; `data-scan-courrier` absent ; 7 tests Scan verts.

### Lot C — Filtres : façade allégée · commit `8f2daf60`
**Constat** : la façade toujours-visible portait « Sans copropriété » + « Hauteur du bâti (LiDAR) » + « Emprise bâtie » (dans « 2 · Le terrain ») et « SDP restante min/max » + « Déjà bâti » (dans « 3 · Capacité »).
**Correctif** : les 5 descendent dans la section repliée **« Affiner la recherche »** (= le « Plus de filtres » du produit : repliable, fermée par défaut, en bas). La façade Capacité ne garde que « Logements possibles ≥ N » et « Activité (destination) ». **Seul l'emplacement change** : les champs lisent/écrivent les mêmes clés (`horsCopro`, `hauteurMin/Max`, `empriseMin/Max`, `sdpMin/Max`, `renouvellement`) via `useFiltre` → prédicats, hash, Mes vues, veille et badge « Filtres (N) » inchangés. Le repli « Affiner » gagne un compteur des filtres actifs qu'il contient (sinon un filtre replié serait invisible).
**Fichiers** : `panel/FiltreLabuse.tsx`. **Tests** : `filters.test.ts` **9 verts** (le round-trip hash/prédicat prouve que la vue sauvegardée avec SDP + copro se rouvre à l'identique, invariant demandé) ; `tsc` 0.

### Lot D — Permis : les deux dessins manquants · commit `8bba8f0c`
**1) Outil Permis (M03)** : chaque permis porte une **pastille d'état** (Badge) + son **type (PC/PA/DP)** dans le libellé (avant : type masqué en mode Dormant). L'état vient de la **même fonction que la fiche** — `ingestion/permits.etat_libelle` / `est_annule` (source unique). Le back `/modules/permis` et `/modules/permis/{id}` servent désormais `etat_libelle` + `annule` au lieu du `_ETAT_LABELS` **local qui divergeait** (il rendait l'état 4 « Chantier ouvert » alors que **4 = ANNULÉ**, corrigé côté fiche par KELFONCIER-FIX-1 Lot C). Pastille : autorisé / travaux commencés / achevés → **vert**, annulé → **rouge**. `_ETAT_LABELS` retiré (mort + trompeur).
**2) Fiche commune, carte « Permis et rythme »** : compteur **PC / PA / DP (+ PD)** et **annulés** sur 12 mois, à côté du chiffre existant. Les données étaient déjà servies (`permis_type_12m` / `permis_annules_12m`, KELFONCIER-FIX-1 Lot C) — **il manquait le rendu**. Même source SITADEL.
**Écart assumé** : le composant `ui/Badge` n'avait que 3 tons (vert/ambre/neutre), **pas de rouge**. Le mandat exige « annulé en rouge » et la maquette v3 distingue des états rouges (`.pill.r`, `.dot.r`, `.tile.r`, verdict rouge) — j'ai ajouté un **4ᵉ ton `rouge`** au Badge (additif : les usages vert/ambre/neutre existants sont inchangés). Il sert aussi la Partie B.
**Fichiers** : `api/modules.py`, `ui/Badge.tsx`, `outils/ModulePanel.tsx`, `contexte/ContextePanel.tsx`, `lib/api.ts`. **Tests** : `test_retours16_permis` mis à jour (état 2 = « autorisé » servi, état 4 = « annulé » — plus le vieux « muet »/« Chantier ouvert ») ; `PermisDouble.test.tsx` : pastille annulé=rouge / autorisé=vert + type ; `test_kelfoncier_permis` vert ; `vitest` 206 ; `tsc` 0.

### Lot E — concept « densifier » routé vers Faisabilité · commit `b7d12c84`
**Constat** : `_CONCEPT_MAP` du Copilote routait « densifier / surélever / construire plus » vers `renouvellement`, **clé morte** (l'outil autonome « Densifier l'existant » a été plié — DENSIFIER-PLI), d'où l'échec `test_portes_concept_toutes_vivantes`.
**Correctif** : la densification est une question de **capacité constructible** → elle vit dans le **Potentiel**, dont l'outil est la **Faisabilité** (`programme`, LIVE). Route re-pointée, mots-clés conservés. **Les 3 chemins du Copilote sont intacts** : seule la table de données `_CONCEPT_MAP` change. Test jumeau `test_copilote_guidage` mis à jour.
**Fichiers** : `copilote_v2/answering.py`, `tests/test_copilote_guidage.py`. **Tests** : suite copilote **138 verts**.

---

## Partie B — l'intérieur des sections de la fiche

### Socle livré · commit `1bb3f728`
`components/fiche/formes.tsx` — les **12 formes**, un composant par forme, **purement présentationnel** (aucune requête, **aucun calcul** : les valeurs, verdicts, « — », « non réglementé » sont rendus tels quels), DA par tokens de l'app (mapping maquette v3 → `var(--…)`), styles inline self-contained (aucun ajout à `index.css`, aucune collision de classe), réutilisant `ui/Bouton` et `ui/Chip` :

| # | Forme | Rôle (maquette v3) |
|---|-------|--------------------|
| 1 | `Verdict` | puce colorée (vert/ambre/rouge/gris) + phrase : réponse en gras, contexte gris |
| 2 | `Tuiles` | grille 2/3 colonnes, style bandeau, variantes ambre/rouge/gris/vert |
| 3 | `Ligne` / `Lignes` | clé → valeur mono à droite, valeur qui passe à la ligne |
| 4 | `Jauge3` | 3 crans faible/moyen/fort + % de parcelle |
| 5 | `BarreEmpilee` | parts + légende |
| 6 | `CasesEtat` | rangée de 4 : ✓ vert / ? ambre / ✕ rouge |
| 7 | `Frise` | segments datés (ancien gris → actuel vert) |
| 8 | `Pastilles` | Chip allumée (date) / éteinte |
| 9 | `Reglette` | repère commune + curseur secteur |
| 10 | `Tableau3` | Zone / Commune / Île, colonne Zone en vert |
| 11 | `Repli` | ◀ + compteur (fermé) · ▼ vert (ouvert) |
| 12 | `OutilsSection` | grille 2 colonnes de Bouton, un seul principal vert |

**Verrou** : `formes.test.tsx`, snapshots des 12 (structure figée, `data-forme` par forme, `Repli` qui ouvre au clic). 12 tests verts.

### Plan de câblage (les 119 lignes → forme, par section)
Référence : `reports/fiche-audit-2/LIGNES.csv` (119 lignes, témoin BZ1065). Aucune ligne n'est retirée : chaque ligne reste rendue, **visible** ou derrière un **`Repli`** avec compteur. Répartition et forme cible :

| Section (maquette) | Lignes CSV | Formes cibles | Replié |
|--------------------|-----------:|---------------|--------|
| En-tête + bandeau 6 chiffres | 9 (`entete`) | inchangé (hors périmètre) + `sect-line` (Lot A) | — |
| Terrain | 7 (`terrain`) | `Verdict` · `Tuiles`×4 · `BarreEmpilee` (CoSIA) + légende · `OutilsSection` (Profil altimétrique) · ligne de sources | — |
| Bâti | 9 (`bati`) | `Verdict` · `Tuiles` (emprise, faîtage LiDAR + badge, usage, RNB) **ou** `Ligne` « terrain nu » · sous-bloc Établissements (`Lignes`, `Repli` au-delà de 3) | Étab. > 3 |
| Identité | 13 (`identite`) | `Verdict` · `Tuiles`×4 (SIREN, créée·état, activité, BODACC) · `Frise` proprios · `Lignes` (détention, filiation) · `OutilsSection`×2 · sources | — |
| Urbanisme | 20 (`urbanisme`) | `Verdict` · `Tuiles`×6 (« — non réglementé » grisé) · alerte AU ambre (`parcel_au_statut`≠ouverte) · `Lignes` (PLU/mixité/DPU/SUP/PEB/RTAA) · `OutilsSection`×4 · `Repli` « N couches sans objet » · sources | couches s.o. |
| Risques | 7 (`risques`) | `Verdict` · `Jauge3` aléas (+ PPR pastille) · `Lignes` ambre (vigilances) · sous-bloc Sans risque (`Repli` CatNat) · `OutilsSection` · sources | CatNat |
| Réseaux | 7+7 (`reseaux`+`viabilisation`) | `Verdict` · `CasesEtat` (voirie·fibre·bus·assainissement) · `Lignes` (raccordement `Repli` indices, stationnement, trafic, solaire) · sous-bloc Gestionnaires · sources | indices |
| Fiscalité | 4 (`fiscalite`) | `Verdict` · `Tuiles`×4 · `Pastilles` dispositifs · `OutilsSection` (TA) · sources | — |
| Marché | 14 (`marche`) | `Verdict` · `Tuiles`×3 · `Reglette` secteur/commune · `Lignes` (valeur estimée, loyers, acquéreur PM) · `OutilsSection`×4 · sources | — |
| Quartier | 8 (`quartier`) | `Verdict` · `Tableau3` (habitants, <25 ans, revenu, permis 36 m) · `Lignes` équipements · `OutilsSection`×2 · sources | — |
| Potentiel | 5 (`potentiel`) + 1 (`gabarit`) | `Verdict` (rouge si construction non autorisée) · `Tuiles`×4 (SDP, capacité, gabarit, hypothèses `Repli`) · `OutilsSection`×2 · disclaimer | hypothèses |
| Simulation | 4 (`simulation`) | `Verdict` prix de sortie · `OutilsSection`×3 | — |
| Pied (actions) | 4 (`actions`) | inchangé (hors périmètre) | — |

Total = **119** lignes (9+7+9+13+20+7+14+4+14+8+6+4+4 ; `reseaux`+`viabilisation` fusionnent dans « Réseaux et desserte »). Toutes conservées, aucune valeur recalculée dans le front.

### Ce qu'il reste à faire (câblage)
Éditer les fichiers de section pour composer ces formes à la place des blocs actuels, sans changer les données : `leBien.tsx` (Terrain/Bâti), `Fiche.tsx` + blocs Identité, `blocks.tsx`/`constructibilite.tsx` (Urbanisme), `risques.tsx`, `reseaux.tsx`, `constructibilite.tsx` (Fiscalité/Potentiel/Simulation), `marche.tsx`, `autour.tsx` (Quartier). Puis, avec l'app lancée : captures avant/après des 3 témoins (AB0134, BZ1065, AB1117), chaque section ouverte, côte à côte avec la maquette ; snapshots des composants déjà en place.

---

## Écarts assumés

1. **Badge 4ᵉ ton `rouge`** (Lot D) — le Badge partagé n'avait pas de rouge ; le mandat (« annulé en rouge ») et la maquette v3 (`.pill.r`, `.dot.r`, `.tile.r`) l'exigent. Ajout **additif**, usages existants inchangés.
2. **« Plus de filtres » = « Affiner la recherche »** (Lot C) — aucune section n'est littéralement nommée « Plus de filtres » dans le produit ; la section repliée/avancée (fermée par défaut, en bas) est « Affiner la recherche ». Non renommée (risque + non demandé).
3. **Concept « densifier » → `programme` (Faisabilité)** (Lot E) — « Densifier vit dans Potentiel » : l'outil autonome ayant été plié, la porte vivante la plus fidèle pour la densification (capacité constructible) est la Faisabilité. Le libellé montré devient « Faisabilité » (une porte réelle, pas un lien mort).
4. **Mapping tokens maquette → app** (Lots A, F) — la maquette utilise `--txt`/`--mut`/`--red` ; l'app utilise `--txt-hi`/`--txt-dim`/`--st-ecartee`. Correspondance appliquée partout.
5. **Captures live absentes** — MCP navigateur déconnecté ; les preuves sont les tests (snapshots, unitaires) et le diff, pas des PNG.

---

## Tests

- `tsc --noEmit` : **0**.
- `vitest run` : **218 passed** (48 fichiers avant → 49 ; +2 assertions Permis, +12 snapshots formes).
- `pytest` ciblé par lot : copilote **138**, permis/commune/modules **verts** (dont `test_retours16` mis à jour, `test_kelfoncier_permis`), `filters` **9**.
- **Baseline pytest complète** : non rejouée intégralement en fin de session (le **run 12 tourne sur la machine** — le mandat l'interdit de perturber — et sature CPU/DB, rendant un run complet long et peu fiable). **2 échecs pré-existants** identifiés au merge, **antérieurs à tout lot** (prouvé sur `367ef2f0`) et **sans rapport** avec ce mandat :
  - `test_retours17_permis::test_w2_cinq_lignes_etat_avec_definitions_sur_les_lignes` — assert une chaîne (« l'instruction déposée n'y figure pas ») **absente de `ModulePanel.tsx` dès le merge** (refactor amont).
  - `test_retours17_permis::test_w3_legende_trois_entrees_quand_permis_actif` — assert `PERMIS_LEGENDE` **absent de `Legend.tsx` dès le merge**.
  Ces deux-là relèvent d'un couplage test↔chaîne cassé par le merge de main, pas de ce mandat ; laissés en l'état (documentés).

---

## Commits (base `367ef2f0`)

```
1bb3f728  Lot F (socle) — les 12 formes de la fiche (maquette v3)
8bba8f0c  Lot D — Permis : les deux dessins manquants
8f2daf60  Lot C — Filtres : façade allégée
6136bfff  Lot A — « Secteur » rentre dans la carte d'en-tête
ba2c0edf  Lot B — Scan patrimoine sans « Courrier » ni « Comparer »
b7d12c84  Lot E — concept « densifier » routé vers Faisabilité (porte vivante)
367ef2f0  Merge remote-tracking branch 'origin/main'
```

Pas de merge vers main. Ports 8545/5745 non lancés en fin de session.
