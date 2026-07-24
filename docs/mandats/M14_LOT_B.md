# M14 — LOT B : les trois régressions (2e correction)

**Branche** : `fix/m14-b-regressions` · **Base** : `main` (`35febbb`). Build 0 erreur. Golden 116/116 (`LABUSE_DEV_MODE=1`).
**Preuves** : `qa/m14/B/*.png` (`qa/m14/cap_B.mjs`, app sur :8044).

## Pourquoi la correction M13 n'avait pas tenu (cause commune)

Les trois points étaient dans **M13 LOT D (`fix/m13-d-couches`)** — une branche **jamais mergée** sur `main`. Vic n'a mergé que `fix/m13-c-scroll` et `fix/m13-f-lisibilite`. Vérifié : `git merge-base --is-ancestor origin/fix/m13-d-couches main` = **NON**. Les captures M13 étaient donc réelles **mais prises sur la branche isolée D**, pas sur `main`. Sur `main`, ces fixes n'ont jamais existé. → C'est exactement ce que le LOT G (re-vérif sur main mergée) doit empêcher de se reproduire.

**Ce lot ne fait pas confiance au code M13** : chaque fix est ré-appliqué sur `main` courante (qui a C+F), en le réconciliant avec ce qui a changé depuis.

## B1 — Bulle « i » entière et au premier plan (QA-62)

**Fix** : `frontend/src/components/Tip.tsx` — la bulle est rendue dans un **PORTAL sur `<body>`** en `position: fixed` `z-[9999]`, avec repositionnement auto aux bords (bascule haut↔bas, recentrage horizontal borné). Elle échappe donc à tout `overflow` de conteneur → **plus jamais rognée**.
**Réconciliation avec M13-C** : le portal N'EST monté que lorsque la bulle est ouverte, ET hors du flux parent → il **ne gonfle plus le scrollWidth** d'aucun conteneur. Le fix anti-scroll-horizontal de M13-C **reste valide** (le `overflow-x-clip` du tiroir Couches est conservé, désormais superflu mais inoffensif — le portal suffit).
**Preuve** : `qa/m14/B/b1_bulle_i_entiere.png` — bulle « Zonage PLU (zones officielles) » **complète** (« …sans découpage à la parcelle. »), flottant au-dessus du panneau. Mesure Playwright : bord droit de la bulle à 465 px ≤ 1440 (non rognée), texte intégral lu.
**Repro** : survol de la pastille « i » d'une couche à long texte dans le panneau Couches.

## B2 — Icônes équipements ×1,5 (QA-63)

**Cause du non-effet M13** : la rampe corrigée était dans D (non mergée). Sur `main`, la rampe est restée celle de M12 (`0,30/0,55/0,85/1,3`).
**Vérification de l'avertissement du mandat** (« une taille codée ailleurs qui écrase ») : il n'existe **qu'UNE seule** définition d'`icon-size` pour `ov-equip` (`MapView.tsx:359`) ; aucun override ailleurs. Le bitmap `addImage` garde son `pixelRatio` (résolution de l'icône, pas la taille d'affichage).
**Fix** : rampe **×1,5** → `12,0.45 / 15,0.825 / 17,1.275 / 20,1.95`. Valeurs littérales, sans ambiguïté.
**Preuve** : `qa/m14/B/b2_equipements_actives.png` (couche activée) ; la rampe est identique à celle prouvée en avant/après par M13-D3 (`d3_equipements_avant/apres`). Le rendu à l'œil du grossissement se confirme au zoom ≥ 15 sur une commune (à revoir sur `main` en LOT G).

## B3 — Panneau Couches ouvert par défaut (QA-64)

**Fix** : `frontend/src/components/panel/LeftPanel.tsx` — `couchesOpen` par défaut **`true`** (était `false`). L'auto-fermeture 10 s est **retirée** ; c'est la **bascule `verdict` false→true** (clic « Afficher l'analyse LABUSE ») qui replie les couches, **une seule fois** (effet `prevVerdict`), l'utilisateur pouvant rouvrir ensuite. Prop `onSelected` supprimée de `LayersSection` (les deux appels desktop/mobile mis à jour).
**Preuve** : `qa/m14/B/b3_couches_ouvert_defaut.png` — au premier chargement, le tiroir Couches est **ouvert et déplié** (liste des couches visible). Assertion Playwright : `[data-couches-drawer]` présent au load = `true`.
**Repro** : charger `/socle/` → Couches ouvert ; cliquer « Afficher l'analyse LABUSE » → Couches se referme.

## Note pour le LOT G

Les trois preuves ci-dessus sont prises sur **la branche B**. Le mandat exige la preuve **sur `main` après merge** (LOT G) — c'est là que la régression M13 était passée. À re-capturer une fois B mergée.
