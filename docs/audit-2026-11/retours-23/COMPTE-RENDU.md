# RETOURS-23 — recette des outils

Branche `fix/retours-23`, worktree `~/Desktop/labuse-outils`, ports 10010 (vite) / 7210 (API).
Pas de merge, aucun accès prod. DA existante conservée, règles de focus/sélection uniques respectées.
Vérifié dans **WebKit** (playwright 1.49.1, webkit-2104, reducedMotion) — une capture par point dans
`captures/`. Hook vert : `tsc -b` 0, vitest **310/310**, build OK, scan secrets OK, pytest unitaires
**3211 passed** (+ 8 nouveaux `test_plu_titre.py`).

> Piège de poste noté : le `.venv` installe `labuse` en editable depuis **un autre worktree**
> (`labuse-ecrans2`). `labuse api` sert donc le code de l'autre arbre. Pour tester CE worktree :
> `PYTHONPATH=…/labuse-outils/src python -m uvicorn labuse.api.app:app --port 7210`.

---

## Règles transversales

### 1. Un seul bouton de retour — « ← Retour » partout, hiérarchique
Mécanisme neuf **`outilSousRetour`** (store) : un outil à plusieurs chemins enregistre son « reculer
d'un niveau » quand il est dans un sous-écran ; le bouton UNIQUE du haut (`PanelRetour`) l'appelle EN
PRIORITÉ (sous-écran → liste des chemins), puis dépile un pont (outil de départ), puis ferme vers le
menu Outils. Le libellé est **toujours « Retour »** (fini « ← Outils »). Échap suit la même priorité.

« ← Retour » **internes retirés** et re-câblés sur le bouton du haut :
- **PLU** (`PluAnnuaire`) : dans une commune → les 24 communes.
- **Communes** : « Acquisitions récentes » → l'accueil des 4 chemins.
- **Scan patrimoine** : toute porte/état → l'accueil des deux portes.
- **Courrier** (`M09`) : étape 3→2→1, puis fermeture.
- **Prospection solaire** : résultat → périmètre → accueil ; `BackBar` ne porte plus que le titre.
- **Estimer un bien** (`AnalyserAnnonce`) : son en-tête propre dit « Retour » (plus « Outils »).

Restent deux « ← Retour » internes dans des écrans **dormants hors menu Outils** (Mon secteur O7 /
Procédure-changement, résolus par deep-link seulement) — non régressifs, laissés en l'état.
Capture : `p01-retour-unique.png` (PLU dans une commune : **1 seul** `[data-retour]`).

### 2. Un seul champ de saisie de parcelle (modèle P19)
La variante à **cadre pointillé** « ◎ ou cliquez une parcelle sur la carte » de `ParcelInput` est
remplacée par le modèle P19 : champ, puis dessous « **— ou — cliquez une parcelle sur la carte** »
(mêmes classes que `EntreeParcelle`). Un seul rendu dans toute l'app. Capture : `p02-scan-p19-input.png`.

### 3. Plus d'ambre pour les liens → vert
- « Fiche → » du tableau des 24 communes (`blocB`) : `hover-jaune` → `text-mint` (mesuré live :
  `rgb(74,222,128)`, `hasJaune:false`). Test `CommunesTable.test` mis à jour.
- « Scan patrimoine → » (Communes / Acquisitions) : `hover-jaune` → `text-mint`.
- « Changer de parcelle » (`EntreeParcelle`) : `ton="ambre"` → `ton="vert"`.
Captures : `p03-fiche-vert.png`, `p12-acquisitions-liste.png`.

### 4. Accordéons & menus à la DA de l'app
- **Liste des communes** (Acquisitions) : le `<select>` natif (liste déroulée par l'OS, hors charte)
  devient un **menu DA** `CommuneMenu` (déclencheur + volet `.floating`, lignes `hover-fill` vert,
  fermeture clic-dehors/Échap) — même grammaire que le menu « Déplacer » du CRM.
- **Accordéons d'« Acquisitions récentes »** : l'accordéon maison (button+Chevron) passe au composant
  **partagé `SousAccordion`** (libellé + compte + chevron). Captures : `p04-communes-menu-accordion.png`.

---

## PLU

### 5. Phrase retirée
Le bandeau ambre « N PLU en révision … N règlements non servis par le Géoportail (…) — texte à
consulter en mairie » est **retiré** de la liste des 24 communes. L'état par commune reste porté par le
badge « révision / RNU / non servi » de chaque carte. Capture : `p05-plu-communes.png`.

### 6. Cartes d'articles (maquette `8-plu-articles.png`)
Carte refaite : **numéro vert mono** (`U 10`), **zone + commune en puces**, **titre en clair** (deux
lignes max), **extrait de trois lignes** (`line-clamp-3`), « **Lire tout ▾** » qui déplie dans la carte,
**pied une ligne** « Règlement du jj/mm/aaaa · p. N » + « PDF ↗ », **premier article mis en avant**
(liseré vert). Capture : `p06-plu-cartes.png`.

Le titre « en clair » n'existait pas au payload : ajouté **côté back** (`plu_titre_corps`,
`modules.py`) — lu EN TÊTE du verbatim (après la réf d'article + tiret/sous-numéro), remis en **casse
de phrase** quand le PDF l'a recopié TOUT EN MAJUSCULES (« ASPECT EXTÉRIEUR… » → « Aspect extérieur… »),
puces Wingdings (U+F000–F0FF) retirées ; `corps` = le verbatim privé du titre (l'aperçu, sans le
répéter). Heuristique pure (aucune ré-ingestion), **8 tests** `tests/test_plu_titre.py`. Vérifié live :
« Hauteur maximale des constructions » / corps « 10.1 - Définition… », titre propre sans puce.

---

## Permis

### 7. Fiche permis dans le panneau de droite (jamais en bulle)
La bulle maplibre (`ouvrirBullePermis`) est **supprimée** (fonction retirée de `MapView`). La fiche
permis s'ouvre désormais dans le **panneau de droite** (`PermitFichePanel`, comme la fiche parcelle,
z-20), que le clic vienne d'une ligne de liste OU d'un point sur la carte (`permisOuvert` → panneau +
surlignage de la ligne). Le contenu est factorisé (`PermitFicheCorps`), partagé avec la modale du bloc
« permis à proximité » de la fiche parcelle (inchangée). « Voir la parcelle » **ouvre la fiche** de la
parcelle rattachée (`select` → panneau droit) + recentre la carte. Capture : `p07-permis-fiche-panneau.png`.

---

## Communes

### 8. Quatre chemins — titre et description sur une ligne
Descriptions raccourcies + `truncate` garde-fou sur titre et description :
- Comparaison communes — « Les 24 communes comparées, triées par colonne. »
- Évolution du marché : ventes et permis — « Ventes DVF et permis, par trimestre. »
- Marché des annonces (Radar) — « Les biens en vente repérés, par commune. »
- Acquisitions récentes — « Changements de propriétaire moral (DGFiP). »
Capture : `p08-communes-chemins.png`.

### 9. Temps de chargement des quatre chemins — mesures avant/après
Mesuré au `curl` sur l'API (port 7210). Le précalcul nocturne **existe déjà** (job `fiche_commune_cache`,
`jobs_impl.py` : `rafraichir_raw_cache` + `rafraichir_contexte_cache` par commune) et sert le cache
persistant `comparateur_raw_cache` / `commune_contexte_cache`.

| Chemin | Endpoint | Avant (cache froid, 1ᵉʳ appel) | Après (cache servi) | Précalcul nuit ? |
|---|---|---|---|---|
| Comparaison communes | `/comparateur-communes` | **1,75 s** | **0,005 s** | ✅ `rafraichir_raw_cache` (nocturne) |
| (liste commune de l'écran) | `/communes` | **5,45 s** | **0,01 s** | ✅ `rafraichir_contexte_cache` (nocturne) |
| Évolution du marché | `/moteurs/barometre` | 0,21 s | 0,10 s | non nécessaire (< 0,5 s) |
| Marché des annonces | `/radar/marche` | 0,03 s | 0,01 s | non nécessaire (< 0,5 s) |
| Acquisitions (par commune) | `/communes/{c}/acquisitions-pm` | 0,55 s | 0,17–0,49 s | à la demande, < 0,5 s servi |

**Conclusion** : les deux seuls endpoints > 0,5 s à froid (comparateur + contexte communes) sont DÉJÀ
servis sous 0,5 s par le job nocturne existant ; les trois autres sont rapides à la demande. Aucun
nouveau précalcul nécessaire. Caches persistants vérifiés peuplés (`comparateur_raw_cache` 12 lignes,
`commune_contexte_cache` 24 lignes).

### 10. Tableau des 24 communes — légende vérifiée contre le calcul réel
Chaque phrase confrontée au SQL (`registre/moteurs/commune.py` + `comparateur.py`) **et** aux 24 valeurs
servies live. **0 écart** :

| Légende | Calcul réel | Verdict |
|---|---|---|
| Instruction = délai médian dépôt→autorisation (mois) | `percentile_cont(0.5) … ORDER BY delai_mois` sur `m10_permit_delais` (logements, délai ≥ 0) | ✅ exact |
| Permis 5 ans = permis SITADEL cumulés sur 5 ans | `WHERE date >= CURRENT_DATE - INTERVAL '5 years'` | ✅ exact |
| Déficit SRU = objectif légal − taux de logement social (points) | `greatest(objectif_pct - taux_lls, 0)` | ✅ exact |
| €/m² ancien = médiane DVF commune entière (ventes strictes) | `prix_ancien_communes` (n ≥ 100) | ✅ exact (jamais « — » : n ∈ [106 ; 7707]) |
| €/m² VEFA = prix VEFA commune observé à l'acte | `neuf_vefa_commune`, seuil 8 | ✅ exact (seuil mesuré = 8 ; 14 communes « — ») |
| €/m² terrain nu = médiane DVF terrain nu par zone PLU (U sinon AU) | `ligne2_terrain_zone` U→AU, seuil 10 | ✅ exact (1 commune « — » : Saint-Philippe) |
| « — » = sous 8 ventes VEFA / sous 10 ventes terrain nu | seuils 8 / 10 | ✅ exact |

### 11. Marché des annonces (Radar)
- **Phrase « Dernière collecte : … » retirée** (`RadarMarche`). La date de collecte reste une mécanique
  interne ; l'explication des fenêtres 30/90 j n'était pas pour le client. Capture : `p11-radar-marche.png`.
- **Pourquoi la dernière collecte date du 27/10** : le Radar est alimenté par **l'extension navigateur
  de Vic** (RADAR-AUTO-1, « à rythme humain »), pas par un cron. La date servie = `max(captured_at)` de
  `pige_passes` ; mesuré en base : la dernière passe (nouvelles + relecture + confirmation) est datée du
  **2026-10-27**. Pour que ça tourne **chaque soir**, il manque un déclencheur automatique côté collecte
  (extension planifiée / collecteur serveur) : aucune des `pige_passes` n'est postérieure au 27/10, donc
  rien n'a tourné depuis. Rien à corriger dans l'outil — c'est la cadence de la source.
- **Cases « — »** : elles viennent bien du **seuil de 5 biens**, pas d'un défaut. Backend `pige/marche.py`
  (`SEUIL_N = 5`, `_mesure` pose `insuffisant=true` et `valeur=null` si `n < 5`) ; le front lit le flag
  `insuffisant` et rend « — » (`m.insuffisant → '—'`). Les compteurs (actives/nouvelles) restent exacts
  dès le 1ᵉʳ bien (jamais masqués).

### 12. Acquisitions récentes — phrase retirée
La ligne « N changements · M acquéreurs — N / M chargés depuis 2022 » est **retirée** : les accordéons
par acquéreur et le bouton « Voir plus » portent déjà le décompte. Capture : `p12-acquisitions-liste.png`.

---

## Scan patrimoine

### 13. Doublon retiré + espacement
L'en-tête interne « Scan patrimoine. Ce qu'un propriétaire possède… » (répété alors que l'en-tête du
panneau Outils le dit déjà) est **retiré**. Les deux chemins sont enveloppés dans une colonne `gap-2`,
**aligné sur l'outil Communes**. Capture : `p13-scan-accueil.png`.

### 14. Clic carte → relance du scan, à chaque clic
`ScanPatrimoine` consomme **lui-même** le clic carte via un effet sur `selectedIdu` (ParcelInput passe en
`withCarte={false} inviteCarte`), actif **dans tous les états** — avant, une fois un propriétaire trouvé
le champ disparaissait et le clic suivant n'était plus écouté. Vérifié live : propriétaire **NEXTIUM**,
clic sur une parcelle d'un autre propriétaire → scan relancé → **ELECTRICITE DE FRANCE**.
Captures : `p14-scan-ownerA.png` → `p14-scan-clic-relance.png`.

### 15. Veille promoteurs — phrase retirée + millésime Sitadel
- **Phrase retirée** : « Ce que les promoteurs, bailleurs sociaux et SEM CONSTRUISENT … Données Sitadel
  au 31/08/2026 » (sous-titre du mode général de `VeillePromoteurs`). Capture : `p15-veille-operations.png`.
- **Millésime Sitadel servi** : `max(date_depot)` de `sitadel_permits` = **2026-08-31** (50 809 permis ;
  cohérent avec le « 31/08/2026 » affiché). Le registre déclare `"2026-07"` (`registre/tables.py`,
  étiquette vitrine, en retard d'un cran).
- **Pourquoi la sentinelle n'a pas injecté plus récent** : il n'existe **aucune entrée de veille/sentinelle
  pour Sitadel** (le millésime est maintenu à la main dans `registre/tables.py`, pas rafraîchi par
  `sentinelle.py`). La donnée en base s'arrête à août 2026 faute d'ingestion plus récente — la sentinelle
  ne « rate » donc pas un millésime plus frais : il n'est pas ingéré. Un millésime plus récent (sept./oct.
  2026) suppose une ré-ingestion Sitadel + une entrée de veille dédiée (hors périmètre de cette recette).

### 16. Libellés des boutons dans leur cadre
« Voir son patrimoine → » / « Masquer sa frise » : le `whitespace-nowrap` (qui débordait à largeur
minimale, cartes imbriquées) est retiré → le texte passe à la ligne, centré, sans sortir du bouton.
Mesuré WebKit : `scrollWidth === clientWidth` (0 débordement) pour les deux. Capture : `p16-veille-boutons.png`.

---

## Fichiers touchés

**Front** : `store/useApp.ts` (outilSousRetour) · `outils/ModulePanel.tsx` (PanelRetour, Courrier,
PermitFicheCorps/Drawer/Panel, ouverture fiche permis) · `outils/PluAnnuaire.tsx` · `lib/api.ts`
(PluExtrait.titre/corps) · `outils/Communes.tsx` (CommuneMenu, SousAccordion, chemins, retour, phrases) ·
`outils/RadarMarche.tsx` · `outils/ScanPatrimoine.tsx` · `outils/VeillePromoteurs.tsx` ·
`outils/ProspectionSolaire.tsx` · `outils/AnalyserAnnonce.tsx` · `outils/blocB.tsx` · `outils/EntreeParcelle.tsx` ·
`ParcelInput.tsx` · `map/MapView.tsx` (bulle permis retirée) · `App.tsx` (PermitFichePanel) ·
`outils/CommunesTable.test.tsx`.

**Back** : `api/modules.py` (`plu_titre_corps` + `titre`/`corps` servis) · `tests/test_plu_titre.py` (neuf).
