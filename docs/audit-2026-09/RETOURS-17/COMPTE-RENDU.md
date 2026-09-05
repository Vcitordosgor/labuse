# RETOURS-17 — panneau Permis : compteurs et états

Branche `fix/retours-12`, **un commit** (petit lot) + ce compte-rendu.
Captures avant/après : `docs/audit-2026-09/RETOURS-17/captures/` (suffixes `-avant` / `-apres`).
Script de recette : `qa/retours17_shots.mjs` (copie locale dans `frontend/` pour l'exécution).

Origine : recette de Vic du 05/09 — « pourquoi ça dit 50k mais j'ai que 5k récents et 15k dormants ? »
Les trois chips (Récent · Dormant · Tous) se lisaient comme une **répartition** alors que deux
étaient des fenêtres de temps et le troisième un total. `Récent 5 580 + Dormant 15 466 = 21 046`,
pas `50 544` — l'écran ne disait pas où étaient les 29 498 manquants (capture `W2-panneau-tous-avant`).

## Une ligne par travail

- **W1 — les 29 498 mesurés avant d'être nommés** : FAIT (§ ci-dessous). Mesuré en SQL sur la base
  servie (q_v11_m137, dmax 2026-07-31) : **70 % sont des permis ACHEVÉS (DAACT déclaré) — 20 534,
  soit 40 % de la base entière**. Le reste (8 964) est un vrai mélange. Le libellé a suivi la
  mesure : les achevés méritent leur **propre ligne** (« Achevés »), le mélange devient « Autres ».
  Décision de structure prise avec Vic (5 lignes plutôt que 4, cf. § W2).
- **W2 — haut du panneau refondu** : FAIT. Bloc total en tête (le total sort des chips) ; « Filtrer
  par état » ; **cinq lignes empilées** (Tous · Récent · Dormant · Achevés · Autres) dont la **somme
  des quatre états fait exactement le total** ; définitions courtes sur les lignes ; bandeau
  d'avertissement raccourci ; « Filtres » renommé **« Affiner »**. **DA existante respectée : aucune
  couleur nouvelle, aucun bleu** (cf. § couleurs). Capture `W2-panneau-tous-apres`.
- **W3 — la carte montre les quatre états** : FAIT. La couleur du point **suit l'état** (avant :
  tout peint en vert → « 47 000 verts, lit 5 580 récents »). Récent **vert** · Dormant **corail** ·
  Achevé/Autre **gris**. **Une seule source de vérité** (`frontend/src/lib/permisEtats.ts`), reprise
  par le panneau, la carte ET la légende. Légende de carte à **trois entrées**, ajoutée quand l'outil
  Permis est actif. Lisibilité vérifiée sur les **4 fonds** (sombre, clair, Ortho IGN, Plan IGN).
  Captures `W3-carte-tous-{sombre,ortho,clair,plan}-apres`.
- **W4 — la règle ailleurs** : FAIT (§ ci-dessous). Balayage des autres compteurs d'états
  (fiche commune, Projets, Veille promoteurs, Radar). Aucun correctif nécessaire côté fiche commune
  ni Projets (déjà honnêtes) ; deux écarts listés pour un autre cycle (Veille, Radar).

---

## W1 — ce que sont les 29 498 (mesuré le 05/09/2026, base locale q_v11_m137, dmax 2026-07-31)

Les quatre états forment une **partition exacte** de la base (chaque permis dans un seul état ;
disjoints par construction — voir la démonstration ci-dessous) :

| État | Définition | Compte | Part |
|---|---|---:|---:|
| Récent | autorisé ≤ 24 mois (fenêtre ancrée sur la fin du flux Sitadel) | 5 580 | 11,0 % |
| Dormant | PC autorisé > 36 mois, sans achèvement (DAACT), parcelle non bâtie | 15 466 | 30,6 % |
| **Achevés** | **travaux déclarés terminés (DAACT)** | **20 534** | **40,6 %** |
| Autres | ni récent, ni dormant, ni achevé | 8 964 | 17,7 % |
| **Total base** | | **50 544** | 100 % |

`5 580 + 15 466 + 20 534 + 8 964 = 50 544` ✅ (la base compte 50 545 lignes : **1 permis à date
NULL** n'entre dans aucun état ET pas dans le total — la partition reste exacte).

Détail des 29 498 « ni récent ni dormant » d'avant :
- **20 534 ont un achèvement déclaré (DAACT)** → **Achevés** ;
- parmi les 8 964 restants (**Autres**) : 3 078 natures DP/PA/PD (pas des PC) · 1 732 PC en période
  intermédiaire (24-36 mois, pas encore dormants) · 4 154 PC anciens sans DAACT mais **non rattachés
  à une parcelle notée du run** (impossible de statuer « dormant » sans la parcelle).

**Libellé choisi d'après la mesure** : les 20 534 achevés sont trop nombreux (40 % de la base
entière) et trop cohérents pour être noyés dans « Autres » — le mandat W1 demandait explicitement
de « le dire plutôt que de tout ranger dans Autres » si un cinquième état le mérite. Il le mérite.
La maquette W2 décrivait quatre lignes / trois couleurs de carte ; le point a été **tranché avec
Vic** : **cinq lignes** au panneau (Achevés séparé d'Autres), **trois couleurs sur la carte**
(Achevés et Autres partagent le même gris — la carte répond « où sont les récents et les dormants »,
le reste est un fond neutre ; le panneau distingue les deux gris par leur nom / définition / compte).

Pourquoi les états sont disjoints (donc la somme = total sans double compte) : Récent (`date ≥
dmax−24 m`) et Dormant (`date < now−36 m`) ont des fenêtres de temps qui ne se recouvrent pas ;
Dormant exige `daact IS NULL` quand Achevé exige `daact` présent ; Autre est explicitement défini
comme « non dormant ». Vérifié : 0 permis dormant hors de la fenêtre 240 mois du total.

---

## W2 — refonte du haut du panneau

De haut en bas (capture `W2-panneau-tous-apres`) :
1. **Bloc total** sur `--surface-1` : `50 544` en 24 px + « permis autorisés en base » ; dessous, en
   12 px, « 47 070 localisés sur la carte · toute la profondeur Sitadel, jusqu'au 31.07.2026 ».
2. **« Filtrer par état »**.
3. **Cinq lignes pleine largeur** : pastille (couleur de carte de l'état) · nom · définition courte
   (12 px `--text-muted`) · compte à droite. Ordre : Tous · Récent · Dormant · Achevés · Autres.
   « Tous » n'a pas UNE couleur → anneau neutre. Achevés et Autres portent la même pastille grise.
4. **État actif** = fond accent `--mint` (contenu inversé sombre `mint-ink`) ; les autres en contour
   hairline, survol vert opaque inversé (règle habituelle de l'app). Un seul actif à la fois.
5. **Bandeau court** : « Sitadel (974) ne publie que les permis autorisés — l'instruction déposée
   n'y figure pas. » (les définitions de Récent/Dormant ont quitté ce paragraphe → sur les lignes).
6. **« Affiner »** (ex-« Filtres ») + les groupes de chips existants dessous, inchangés.

Le total, les localisés et la date, désormais dans le bloc en tête, ont quitté le pied ; le pied ne
dit plus que le vivant de la vue active (sur la carte · chargés · zone dessinée).

### Couleurs — DA existante, aucune teinte nouvelle, aucun bleu

Source unique `frontend/src/lib/permisEtats.ts`, qui **tire des tokens existants** (jamais un hex neuf) :

| État | Couleur | Token | Nouveau ? |
|---|---|---|---|
| Récent (+ état actif) | vert de marque `#4ADE80` | `TOKENS.mint` | non |
| Dormant | corail `#E2726A` | `TOKENS.coral` (couleur historique du dormant, inchangée) | non |
| Achevé / Autre | gris neutre `#6B7A72` | `st-exclue` (déjà dans `tailwind.config.js`) | non¹ |
| Bandeau d'avertissement | note d'info discrète existante (`text-txt-dim`), pas de fond coloré | — | non |

¹ `st-exclue` `#6B7A72` existait dans la palette Tailwind mais **manquait au miroir JS `tokens.ts`** :
ajouté (`TOKENS.stExclue`) pour que la source unique n'ait aucun hex en dur. Sémantiquement juste :
« exclue/hors entonnoir » = achevé/bâti, hors des opportunités. Aucun bleu (réservé aux liens
SIREN/SIRET). Aucun besoin de couleur non couvert par ces règles n'a été rencontré.

---

## W3 — la carte à trois couleurs, cohérente avec le panneau

- La couleur d'un point permis suit `properties.etat` (`recent` | `dormant` | `gris`), peinte depuis
  `PERMIS_ETAT_COLOR` (même source que les pastilles). L'ancienne bascule binaire `point_mort`
  (vert/rouge) a disparu du rendu carte.
- En « Tous », les trois couleurs coexistent (le corail dormant posé après le gris/vert → il prime).
  En Récent/Dormant/Achevés/Autres, la carte ne montre que la couleur de l'état actif.
- Légende de carte : **trois entrées** (Récent · Dormant · Achevé ou autre), affichée quand
  `module ∈ {permis, promesses}`, avec la note « Achevé et Autre partagent le même gris ; le panneau
  les distingue par leur compte ».
- **Lisibilité vérifiée sur les 4 fonds** : sombre, clair, Ortho IGN, Plan IGN (captures
  `W3-carte-tous-*-apres`). Le gris `#6B7A72` reste lisible sur fond clair grâce au contour sombre
  du point (`circle-stroke #0b0f14`). Effet mesuré : sur `W3-carte-tous-sombre-avant` la carte est
  quasi uniformément verte ; sur `-apres`, les points verts ≈ le compte « Récent ».

---

## W4 — la même règle ailleurs

Balayage des écrans qui affichent des compteurs d'états côte à côte :

| Écran | Somme = total ? | Couleurs liste = carte ? | Verdict |
|---|---|---|---|
| **Projets** (`ProjetsPanel.tsx`) | **OUI** — `retenue + écartée + à analyser + proposée = vivier` (partition réelle) | pas de couleur par état (texte neutre) | **conforme, rien à corriger** |
| **Fiche commune** — bloc « Permis & délais » (`ContextePanel.tsx` l. 368-379) | pas de total revendiqué ; chaque métrique porte son libellé (« Permis autorisés 12 mois », « Permis dormants ») | pas de couleur par état | **conforme** (règle « aucun nombre sans son périmètre » déjà tenue) — rien à corriger |
| **Fiche commune** — bloc « Foncier repéré » (l. 463-476) | métriques distinctes libellées (parcelles · stock repéré · densifiables) | pas de couleur par état | **conforme** — rien à corriger |
| **Veille promoteurs** (`VeillePromoteurs.tsx` l. 243) | « N opérations · M logements · P affichées (plafond) » : `P` est une **troncature**, pas une part | pas de couleur par état | écart mineur (le « affichées » se lit comme une sous-part) — **à reprendre au cycle Veille** |
| **Radar** (`RadarView.tsx` l. 541) | « N biens · M sur la carte » : `M` est un **sous-ensemble** (rattachés), pas une part ; + couleurs de statut **en dur dans MapView**, pas de source unique | non (hex en dur côté carte) | **laissé au compte-rendu** (autre cycle, comme prévu au mandat) |

Conformément au mandat, la fiche commune et Projets étaient déjà honnêtes (rien « d'une ligne ou
deux » à corriger) ; Veille et Radar sont **listés** pour un cycle dédié, pas corrigés ici.

---

## Recette

- **Backend** (`api/modules.py`) : `/modules/permis` accepte `etat=recent|acheve|autre` (whitelist
  fermée ; `dormant` garde `/promesses`). Partition vérifiée par endpoint : `recent + dormant +
  acheve + autre == total` (test `test_retours17_permis.py::test_w1_w2_partition_exacte`).
  Coût mesuré : compteur achevé 11 ms · liste/compteur autre ≈ 560 ms (payé seulement quand le
  filtre « Autres » est actif ; le compteur d'entrée « Autres » est **dérivé** = total − les trois
  autres, pour garantir la somme sans payer ce COUNT au montage).
- **Tests** : nouveau `tests/test_retours17_permis.py` (6 tests : partition exacte, whitelist,
  cinq lignes + définitions, source unique des couleurs, légende 3 entrées). Deux gardes RETOURS-16
  (`test_v3…`, `test_v4…`) **mises à jour** vers la vérité RETOURS-17 (définitions sur les lignes,
  total dans le bloc en tête).
- Suite pytest : voir dernière ligne de session. `vitest` : **171 passed** (36 fichiers). `tsc` : 0
  erreur. `vite build` : OK.
- **Golden** : intact — ce mandat ne touche **aucun fichier de scoring** (endpoint permis + front +
  couleurs + tests uniquement).
- Captures Playwright (`chromium-1217`, 1440×900 ×2) : panneau (5 états + chaque état isolé) et
  carte (4 états, 3 couleurs, légende) en **avant/après**, sur sombre / ortho / clair / plan.

## Pièges rencontrés

- Le module playwright ne se résout que depuis `frontend/` (copie locale du script de recette, comme
  RETOURS-16). Chromium : `chromium-1217` (exécutable Google Chrome for Testing).
- Un ancien `uvicorn` servait sur `:8000` (code périmé) — tué et relancé avant les captures
  (`lsof -ti tcp:8000 | xargs kill`). Serveur relancé avec `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`.
- Captures « avant » obtenues par `git stash` des fichiers suivis + rebuild + relance, puis
  `git stash pop` + rebuild (le `permisEtats.ts` untracked reste inerte tant que l'ancien code ne
  l'importe pas).

Un commit pour le lot. **Je ne merge pas.**
