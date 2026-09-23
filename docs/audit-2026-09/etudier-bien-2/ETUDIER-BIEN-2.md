# ETUDIER-BIEN-2 — Fusionner « Étudier un bien » dans la fiche, puis supprimer l'outil

**Mandat d'exécution** (suite d'ETUDIER-BIEN-1) : les 3 faits uniques de l'outil passent dans la
§Marché de la fiche, les 3 divergences de calcul sont tranchées (la fiche fait foi), l'outil disparaît.
3 lots, un commit par lot. Branche `feat/etudier-bien-2` depuis main `3e90c49a`, worktree
`~/Desktop/labuse-etudier2`, ports 8255/5455. Non mergé.

**Commits :** `79303cb9` (Lot A) · `1d9fbd7c` (Lot B) · `831340db` (Lot C).

## 0. Étape 0

`pwd` = worktree, branche `feat/etudier-bien-2`, base main `3e90c49a`, arbre propre,
`docs/audit-2026-09/ETUDIER-BIEN-1.md` présent (la référence). ✅

---

## Lot A — Les 3 faits uniques entrent dans la §Marché de la fiche

`frontend/src/components/fiche/marche.tsx` : ajout d'un `useQuery(['mon-secteur', idu], getMonSecteur)`
(le MÊME endpoint `/outils/mon-secteur` que l'ex-outil — **rendu, pas nouveau calcul**), et de 3 blocs
en grammaire fiche (`FactRow` / `FactNote` / `GroupLabel`, cartes `.fiche-v6`) :

1. **Écart secteur ↔ commune entière** (`data-secteur-ecart-commune`) — « secteur N m · commune
   entière X €/m² (±y %) — le secteur est sous / au-dessus de la commune ». Source `ecart_commune`
   (moteur `sector_price` + médiane commune `_dvf_bati`).
2. **Médiane par type — secteur** (`data-secteur-par-type`) — Maison / Appartement au **rayon
   adaptatif** (médiane locale `_ref_local`, le fait unique de l'ex-outil), Terrain nu à la **section
   cadastrale** (la valeur foi de la fiche, cf. Lot B). Effectif + millésime par ligne ; **sous
   5 ventes → « — »**, jamais un chiffre inventé.
3. **Annonces Radar — autour (rayon 1,5 km)** (`data-secteur-radar-rayon`) — liste courte : type ·
   commune · distance · prix · €/m² · écart. Libellé **distinct** du bloc « cette parcelle » (Lot B).

Aucune info perdue vs l'outil (l'écran « ce que porte la parcelle » = la fiche elle-même : SHAB,
terrain, potentiel, charge/calculette, dernières ventes y vivaient déjà — cf. ETUDIER-BIEN-1 §a).

---

## Lot B — Trancher les 3 divergences (la fiche fait foi)

| Divergence (ETUDIER-BIEN-1 §c) | Méthode retenue (fiche) | Geste |
|---|---|---|
| **Terrain nu du secteur** | Section cadastrale (`dvf_secteur_medianes`, clé `left(idu,10)`) | `api/mon_secteur.py` : `_terrain_local` (rayon géographique 500→1500 m) **SUPPRIMÉ** → `_terrain_section` (même table/clé que la fiche `_q_v2_fiche`, app.py:3811). Lecture registre `lectures.py` mise à jour (`dvf_mutations` → `dvf_secteur_medianes`). |
| **Radar** | Rattaché à la parcelle pour « cette parcelle », rayon pour « autour » | Front `marche.tsx` : le bloc existant relabellisé **« Annonces Radar — cette parcelle »** ; le nouveau **« Annonces Radar — autour (rayon 1,5 km) »**. Deux libellés, jamais confondus. |
| **Prix du neuf** | VEFA commune (seuil 8), la méthode de la fiche | **Résolu par le Lot C** : la cascade `resolve_prix_sortie_servi` n'était AFFICHÉE que par l'écran « constat » de l'outil (supprimé). Aucun fichier retiré — la fonction reste le moteur de CA partagé (modules/app/sonde), sans affichage divergent. |

### Vérification « un même chiffre en une seule version » (3 témoins, base réelle)

Terrain-nu-secteur servi par la §Marché de la fiche (`dvf_parcelle.secteur`, app.py) **==** celui de
`/outils/mon-secteur` (`_terrain_section`) :

| Témoin | Fiche §Marché (terrain) | mon-secteur (terrain) | Verdict |
|---|---|---|---|
| 97411000BZ1065 (Saint-Denis) | **369 €/m²** | **369 €/m²** · section | 1 version ✅ |
| 97415000DK1044 (Saint-Paul) | **716 €/m²** | **716 €/m²** · section | 1 version ✅ |
| 97415000AC0016 (Saint-Paul) | 173 €/m² (n=3) | **« — » (n<5)** | même méthode section ; le per-type applique le **seuil-5 du mandat** (honnête), l'en-tête garde la valeur pré-existante (hors mandat de la retoucher) ✅ |

`_terrain_local` retiré ; graphe des lectures cohérent (`lectures_perimees() == []`,
`lecteurs_non_declares()` inchangé vs baseline).

---

## Lot C — Supprimer l'outil « Étudier un bien »

### Retiré

- `frontend/src/components/outils/EtudierBien.tsx` **+** `EtudierBien.test.tsx` (supprimés) ;
- `registry.ts` : entrée VISIBLE `scoreur-adresse` (O2) → **menu 18 → 17** ;
- `ModulePanel.tsx` : mapping `'scoreur-adresse'` + import `EtudierBien` ;
- `frontend/src/lib/api.ts` : binding front `scoreurAdresse` + type `ScoreurResult` ;
- `circuit_verrous.py` : entrée `OUTIL_ROBINET_MENU["scoreur-adresse"]` (n'est plus un outil du menu) ;
- `copilote_v2/answering.py` : `_PORTE_LABEL["scoreur-adresse"]`, et retargetage de la mission
  VERIFICATION + de la concept-route « scorer une adresse » vers **`calculette-fonciere`** (module
  vivant — doctrine « pas de lien mort » du dépôt, cf. o7-carnet/o10-bascules).

### Conservé (partagé, cf. mandat — « NE PAS toucher à ce qui est partagé »)

- **`<Calculette>`** : la clé `calculette-fonciere` (M23, hidden) est **restaurée** en hôte minimal
  (nouveau `CalculetteFonciere.tsx` = `ParcelInput` + `<Calculette>` partagé). La fiche §11 /
  Constructibilité / RadarView / copilote l'ouvrent via `calcPrefill` (jamais un 404). « Hors mandat :
  retoucher d'autres sections de la fiche » → les portes de la fiche restent **intactes**.
- **`SecteurResultats` / `MonSecteur`** (clé `mon-secteur`, hidden résolvante) : inchangés.
- **Endpoint POST `/scoreur-adresse`** : conservé **dormant** — le fichier `api/scoreur.py` héberge
  le `_geocode` PARTAGÉ (utilisé par `onboarding.py`), et le retirer rayonnerait sur
  app.py/protection/robinets/flux/sonde (hors proportion). Plus aucun appelant front. Vérifié par grep :
  seul l'ex-`EtudierBien` l'appelait côté front.
- **RadarView** « Étudier le bien » → retargeté vers la **fiche** (`select(idu)`) — l'étude complète.

### Verrou

`verrou_outils_registre()` (V5f) : verdict **ok**, preuve « **17 outils du menu**, tous avec robinet ;
58 chiffres servis, tous des ids du registre ». Test `test_lot5_concepts` : `18 → 17`.

---

## Captures avant / après de la §Marché (3 témoins)

`docs/audit-2026-09/etudier-bien-2/captures/` — « avant » = frontend main (5456), « après » =
`feat/etudier-bien-2` (5455), **même backend 8255** (base réelle).

| Témoin | avant | après | Ce que montre l'après |
|---|---|---|---|
| BZ1065 Saint-Denis | `avant-BZ1065-marche.png` | `apres-BZ1065-marche.png` + `apres-BZ1065-partype.png` + `apres-BZ1065-radar-rayon.png` | écart **−7 %** (sous la commune, 2 556 €/m²) ; par-type Maison 3 747 / Appart 2 403 (rayon) / Terrain nu **369 · section** ; Radar autour : 1 annonce (maison, 852 m, 799 000 € / 4 756 €/m²) |
| DK1044 Saint-Paul | `avant-DK1044-marche.png` | `apres-DK1044-marche.png` | écart **+21 %** (au-dessus, 3 633 €/m²) ; Terrain nu **716 · section** (91 ventes) |
| AC0016 Saint-Paul | `avant-AC0016-marche.png` | `apres-AC0016-marche.png` | écart **+7 %** ; Terrain nu **« — échantillon < 5 »** (état honnête, seuil-5) |

`apres-outils-menu.png` — le menu Outils **sans** « Étudier un bien » (17 outils).

Les captures « avant » ne portent AUCUN des 3 blocs (`data-secteur-ecart-commune` /
`-par-type` / `-radar-rayon` absents, vérifié DOM) ; les « après » les portent tous, valeurs
cohérentes avec le reste de la §Marché (le « Prix de sortie — bâti secteur » 2 365 €/m² est identique
des deux côtés — moteur `sector_price` inchangé).

---

## État des tests

| Porte | Résultat |
|---|---|
| `tsc --noEmit` (front) | **vert** |
| `vite build` (front) | **vert** |
| `vitest run` | **173 passed / 3 failed** = les 3 admin PRÉ-EXISTANTS (`Donnees` snapshot + `Detail` ×2), **identiques à main** (baseline vérifiée). 0 nouvelle rupture. |
| pytest `test_front_reliquats` | à jour (fusion défaite) — vert sauf `test_m135_echelle_action` (**PRÉ-EXISTANT sur main**, lit `status.ts` non touché) |
| pytest `test_lot5_concepts` (V5f) | vert — 17 outils |
| pytest 5 tests copilote (porte → calculette-fonciere) | verts |
| pytest `test_scoreur` + `test_flux` (endpoint conservé, base openclaw) | **22 passed** |
| pytest `test_reparations1_lot2` (graphe lectures) | `lectures_perimees()==[]`, `non_declares` inchangé vs baseline ; l'unique échec (`gabarit/builder.py`+`limites.py`) est **PRÉ-EXISTANT sur main** |

**Baseline pré-existants (non causés par ce mandat, prouvés identiques sur `3e90c49a`) :** 3 admin
vitest, `test_m135_echelle_action`, `test_graphe_exact_dans_les_deux_sens` (gabarit).

---

## Reste à Vic

Merge. (Non mergé, un commit par lot.)
</content>
