# OUTILS-3 — finition (recette écran de Vic sur OUTILS-2) · compte-rendu

Poste : `~/Desktop/labuse` · branche : `feat/outils-1` (8 commits : radar-depot-2 ×5 + maquette + OUTILS-1
`e9278b3e` + OUTILS-2 `ac5b53a5`). **Ne pas merger** — commande au dernier point, isolée.

Écriture Postgres : **aucune** — le diagnostic F1 a montré qu'aucune migration/ré-ingestion n'était
requise (voir F1). Golden : 0 fichier de scoring touché → intact.

**Preuve que la branche est servie** : API redémarrée (uvicorn tué/relancé), front **rebâti** (`npm run
build`), servi sous `/socle/`. Endpoints O2/O3 répondent (`/parcels/{idu}/geojson`, `annee_creation` +
`naf_label` sur zone, millésime réel « SIRENE géolocalisé 2026-08 »). Captures Playwright sur ce build.

---

## F1 — CONCURRENTS : le diagnostic, noir sur blanc

**Ce que Vic a vu** : « CHANTECLAIR · depuis 2006 » servie comme concurrent boulangerie alors qu'elle a
fermé, remplacée par « CAP MÉCHANT » absente.

**Diagnostic (vérifié en base ET dans le parquet source, pas deviné) :**

1. **L'état administratif EST filtré** : l'ingestion ne charge que `etatAdministratifEtablissement = 'A'`
   (`ingestion/sirene_etablissements.py`), et la requête concurrents filtre `WHERE naf = :naf AND actif`
   (`zone.py`). Le filtre « seuls les actifs » est donc bien en place, aux deux étages.
2. **CHANTECLAIR (SIRET 49134419800016) est ENCORE 'A' (active) dans le parquet SIRENE 2026-08 lui-même**
   (état='A', dernier traitement 2025-12-06). La fermeture réelle **n'est pas encore dans la source
   INSEE** — c'est un **retard de source**, pas un défaut de filtre. Aucune ré-ingestion ne la retirerait
   (elle est 'A' au dernier millésime). On ne peut pas inventer sa fermeture.
3. **CAP MÉCHANT n'est PAS une boulangerie** : toutes ses occurrences en base sont en **NAF 5610A
   (restauration)** — « LA BRASSERIE BY LE CAP MECHANT » à Saint-Denis, etc. Elle n'apparaît donc pas,
   à juste titre, dans les concurrents **boulangerie (1071C)**. Il n'existe aucun établissement 1071C
   « CAP MÉCHANT » en base.

**Correctifs livrés (transparence, pas d'invention) :**
- **Millésime RÉEL affiché** sous le bloc concurrents (« Source SIRENE géolocalisé 2026-08 (INSEE) ») —
  lu depuis `sirene_etablissements.millesime` (pas le libellé générique de `data_sources` que
  `seed_sources` peut clobberer). Mention explicite : « une fermeture très récente peut ne pas encore y figurer ».
- **NAF lisible** : « Boulangerie et boulangerie-pâtisserie » (via `naf_labels.label`), le code « 1071C »
  passe en second plan / survol.
- **« Établissement (nom non diffusé) »** : gardé (ils existent) + mention courte « certains noms sont
  masqués à la demande de l'établissement (diffusion INSEE restreinte) ».

**Check** : sur la zone témoin, les 33 concurrents servis = le `count(*) … WHERE naf='1071C' AND actif
AND ST_Contains(zone, geom)` — par construction (la requête EST ce filtre). Aucun établissement fermé ne
passe (aucun n'est en base : tous ingérés étaient 'A').

**Aucune écriture DB** : le filtre est correct, une ré-ingestion ne changerait pas le cas (source lag).

---

## F2 — PERMIS : « Tous » affiche enfin les points morts ✅ (bug réel corrigé)
`ModulePanel.tsx` (M03).
- **Bug trouvé** : le `months` du point mort mesure la DORMANCE (« PC plus vieux que N mois »), sémantique
  INVERSE du radar (« derniers N mois »). Mon « Tous » (OUTILS-2) mettait `months=240` pour les deux → le
  point mort devenait « plus vieux que 240 mois » = **0 résultat** (d'où l'absence de rouge).
- **Correctif** : `pmMonths = pointMort ? months : 36` — en « Tous », le point mort garde sa fenêtre de
  caducité (36 mois) pendant que le radar élargit à tout. Les deux jeux se superposent, le rouge par-dessus le vert.
- **Vérifié (capture)** : la carte « Tous » montre **vert (en cours) ET rouge (point mort) coexistants**.
  Compteur « **Tous 21 088** » = 5 613 (en cours) + 15 475 (point mort) — le check tient.

## F3 — PERMIS : le vide noir supprimé ✅
- **Cause** : le wrapper interne d'`AddressAutocomplete` est `flex-1` ; placé en enfant direct du flex-COL
  du panneau (OUTILS-2), il grandissait VERTICALEMENT (~300 px de vide). **Correctif** : enveloppe
  non-flex. **Vérifié** : l'écart recherche→segment passe de ~300 px à **8 px**.

## F4 — COURRIER : le PDF porte le corps ✅
`api/courrier.py`.
- Le rendu marchait en fpdf2 2.8.7 (prouvé : extraction texte = corps complet), MAIS le défaut `new_x/new_y`
  de `multi_cell` **varie selon la version** (`new_x=RIGHT, new_y=TOP` sur certaines → curseur qui ne
  descend pas, lignes écrasées = exactement le symptôme). **Correctif robuste** : positionnement
  **explicite** `new_x=LMARGIN, new_y=NEXT` (en-tête + chaque ligne) → le corps s'imprime quelle que soit
  la version. **Vérifié** : PDF de test = 9 lignes, corps présent (« Madame… » … « Cordialement »),
  variables `{parcelle}{commune}{surface}` substituées comme à l'écran.

## F5 — PROJETS : accès à l'outil Courrier ✅
`ProjetsPanel.tsx`. Bouton « **Nouveau courrier →** » dans Projets → Mes courriers →
`setView('cartes')` + `setModule('courriers')` (ouvre l'outil à l'étape 1).

## F6 — COMMUNES : « voir ses parcelles » bascule sur CARTES ✅
`ContextePanel.tsx`. Le bouton fait désormais `setCommune(commune)` puis `setView('cartes')` : on QUITTE
l'analyse (Outils, fiche fermée) pour l'EXPLORATION (onglet Cartes, Couches + Filtres, commune = périmètre
actif). `setView('cartes')` ne réinitialise pas `commune` (posée avant).

## F7 — REMONTER LE TEMPS : « 🔒 après fixe » retiré ✅
`ModulePanel.tsx` (M08) — mention sans sens pour le client, supprimée (choix de Vic).

## F8 — ÉTUDE DE ZONE
- **Pastilles cliquables + légende** ✅ (`MapView.tsx` + `EtudeZone.tsx`) : la pastille orange concurrent
  ouvre un popup (nom, activité lisible, « depuis AAAA », **« voir la parcelle → »** via `parcelAt`).
  Contenu construit en DOM (`textContent`) → aucune injection. Légende courte ajoutée sous le bloc.
- **Parcelles sous l'isochrone** — **diagnostic** : `ile-fill` est **visible**, **19 780 parcelles
  rendues** sous l'isochrone (zoom 13, opacité normale) ; le fill d'isochrone (`module-zone-fill`, vert
  0,08) ne masque rien. La disparition décrite **ne reproduit pas** sur le build reconstruit (capture
  `08-zone-isochrone-F8.png` : parcelles + isochrone visibles). Aucun code fautif trouvé ; documenté.

## F9 — « SOUS LE MARCHÉ » : trois garde-fous ✅ (mesurés)
`pige/signaux.py`.
- **Échantillon insuffisant** : `_badge` renvoie `calculable:False` (donc **pas de badge**) quand
  `n < SEUIL_N` (constante nommée `SEUIL_N = 5`). En place, vérifié.
- **Surface fiable** : `_badge` renvoie `None` si surface manquante/≤ 0 — en place, vérifié.
- **Référence + millésime TOUJOURS portés** : le détail affiche « réf. {périmètre} {€/m²} · {millésime
  DVF} (n=…) » ; la **pastille compacte** porte désormais la même référence en survol (`title`) — jamais
  un « −19 % » orphelin.
- **Distribution mesurée** (corpus actuel, 106 biens non-à-qualifier) : 4 sans badge (surface manquante),
  **0** réf. de zone insuffisante, 102 écarts calculables, **13 badgés « sous le marché » (≤ −15 %)**.

## F10 — PÉRIMÈTRES : prouvés sur BZ1065 ✅
Capture `06-etudier-BZ1065-perimetres-F10.png` : « Étudier un bien » sur BZ1065 affiche **« résiduel, bâti
conservé : 26 m² »** et **« … terrain libéré » (SHAB vendable 123 m²)** — les deux libellés + les deux
chiffres (assertions automatiques : bâti conservé ✓, terrain libéré ✓, 26 m ✓, 123 m ✓). Données live :
fiche `potentiel_transformation.sdp_residuelle_m2 = 26`, scoreur `constat.sourced.shab_vendable_m2 = 123`.
Les libellés viennent de la source unique `lib/perimetres.ts` (fiche, Étudier, Comparaison).

## F11 — RADAR : « Immeuble » retiré des filtres ✅ (ajout Vic)
`RadarView.tsx` — `TYPES` sans « immeuble » (hors périmètre de la pige).

---

## Gates

- **tsc** : 0. **build** : OK. **vitest** : **108/108** (tests de recette Permis/EtudierBien à jour).
- **pytest** : **2000 passed, 42 skipped, 0 failed** (347 s, `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`
  contourne le piège WeasyPrint/`libgobject` FZ-002).
- **Golden** : **0 fichier de scoring touché** → intact.
- **Écriture DB** : **aucune** (F1 = source lag, pas de migration).

---

## Fichiers touchés

Backend : `zone.py` (millésime réel + naf_label concurrents) · `api/courrier.py` (PDF new_x/new_y).
Front : `outils/ModulePanel.tsx` (Permis F2/F3, F7) · `outils/EtudeZone.tsx` (F1 concurrents, F8 pastilles/légende) ·
`outils/RadarView.tsx` (F9 title, F11 immeuble) · `projets/ProjetsPanel.tsx` (F5) ·
`contexte/ContextePanel.tsx` (F6) · `map/MapView.tsx` (F8 popup) · `lib/types.ts` (naf_label).
Docs : `docs/OUTILS-3/` (compte-rendu, captures).

---

## Merge

**Ne pas merger.** Après revue Vic :

```
git checkout main && git merge --no-ff feat/outils-1
```
