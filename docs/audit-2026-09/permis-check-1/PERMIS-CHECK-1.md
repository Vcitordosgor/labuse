# PERMIS-CHECK-1 — Outil Permis : données justes + 4 points

Branche `fix/permis-check-1` (worktree `~/Desktop/labuse-permis`, base main `51c3cdfd`). Ports 8195/5395.
Mandat d'exécution : on vérifie, on corrige, une capture avant/après par point visuel, la preuve data pour les points données.

| Point | État | Nature |
|---|---|---|
| P1 — contour du chevron sur fond vert | **FAIT** | CSS (composant chevron partagé) |
| P2 — phrase de résultat parcelle sans/avec permis | **FAIT** | front + preuve data |
| P3 — accès de la recherche à tout le parc / adresse collée | **FAIT (corrigé)** | back (normalisation libellé) + preuve data |
| P4 — retirer la ligne « … localisés sur la carte · … » | **FAIT** | front |

Portes : `tsc -b` vert · `vite build` vert · vitest **178 pass / 3 échecs admin PRÉ-EXISTANTS** · tests recherche/adresses **13/13** (dont la régression P3) · pytest full **19 échecs / 3252 pass**, les 19 sont les échecs d'environnement `*_base_reelle` PRÉ-EXISTANTS (aucun dans recherche/adresse/constants ; `test_w2` et `deps_declared` vérifiés sans lien avec les modifs).

---

## P1 — Contour du chevron ouvrir/fermer visible aussi sur fond vert

**Cause.** `frontend/src/styles/index.css` (règle RETOURS-19) : quand une barre d'accordéon
(`.hover-fill`) passe en fond plein vert au survol, la boîte du chevron recevait
`border-color: transparent !important`. Le contour n'existait donc plus que sur fond sombre
(la bordure `--line-2`, foncée, disparaît sur le vert). Constat Vic exact.

**Correction.** Même geste que la tuile d'icône `.itile` (RETOURS-19 Y2) : sur l'aplat, la boîte
garde un **fond transparent** (pas de carré sombre sur le vert) mais reçoit un **contour ré-encré
en sombre** — `rgba(7,16,9,.34)` sur vert/ambre, `rgba(20,14,34,.38)` sur mauve. Corrigé dans le
**composant partagé** (`ChevronSection` / règle CSS), pas bouton par bouton : les trois barres
« Filtrer par état », « Affiner », « Voir les permis » en héritent, comme tout autre chevron de l'app.

**Preuve (styles calculés, barre « Affiner » survolée = fond vert dégradé).**

| | contour du chevron | fond du chevron |
|---|---|---|
| AVANT | `rgba(0,0,0,0)` (invisible) | transparent |
| APRÈS | `rgba(7,16,9,0.34)` (visible) | transparent |

Captures : `captures/p1_before.png` (chevron nu sur le vert) · `captures/p1_after.png` (boîte au contour visible).

---

## P2 — Phrase de résultat quand une parcelle est ciblée

**Avant.** Cibler une parcelle sans permis n'affichait qu'une note laconique ; une parcelle AVEC
permis ouvrait d'office le 1ᵉʳ permis (aucun compte lisible). Choisir une adresse/parcelle dans le
suggest ne déclenchait même pas la recherche de permis.

**Correction (`frontend/src/components/outils/ModulePanel.tsx`, M03).** Une **phrase de résultat est
toujours affichée** quand une parcelle est ciblée (IDU saisi OU adresse/parcelle choisie dans le
suggest — `onSelect` déclenche désormais la recherche). L'ouverture automatique du 1ᵉʳ permis est retirée.

- **0 permis** → « Aucun permis sur cette parcelle `<idu>` sur les **240** derniers mois (Sitadel au …) ».
- **≥ 1 permis** → « `<X>` permis sur cette parcelle `<idu>` — cliquez les points sur la carte ».

**N = 240 mois**, lu dans le code (`MONTHS_RADAR = [12, 24, 48, 72, 240]`, `240 = « Tout » ≈ toute la
profondeur Sitadel servie`) — la profondeur max de l'outil. Le compte vient de `/modules/parcelle-permis`
(permis autorisés géolocalisés ≤ 200 m, `via_permits_geo` — la même source que le signal viabilisation
de la fiche ; endpoint non fenêtré en temps → N = la profondeur max annoncée).

**Preuve data (base réelle, endpoint `/modules/parcelle-permis`) — 2 IDU testés :**

| IDU | commune | attendu (base) | affiché (UI) | phrase |
|---|---|---|---|---|
| `97419000AK0762` | Sainte-Rose | 0 | 0 | « Aucun permis sur cette parcelle AK 0762 sur les 240 derniers mois (Sitadel au 2026-07-31). » |
| `97411000CH0196` | Saint-Denis | 6 | 6 | « 6 permis sur cette parcelle CH 0196 — cliquez les points sur la carte. » |

Attendu = affiché dans les deux cas. Captures : `captures/p2_zero.png`, `captures/p2_avec.png`.

---

## P3 — La recherche a-t-elle accès aux ~431k parcelles (priorité)

**Reproduction.** « 1 bis Chemin de la Citerne, 97417 Saint-Denis » (collé depuis une fiche) →
**0 résultat** avant correction.

**Cause EXACTE.** La barre de recherche (composant partagé `AddressAutocomplete` →
`GET /api/recherche/suggest` → `_sugg_adresse`, jumeau `/adresses/autocomplete`) cherchait la saisie
comme **sous-texte de la SEULE colonne `numero || ' ' || voie`** (« 1 Chemin de la Citerne »). Or le
libellé de fiche (`_fmt_ban`) s'écrit `« {numero} {rep} {voie}, {code_postal} {commune} »` : le **rep
(« bis »)**, le **code postal (97417)** et la **commune (Saint-Denis)** n'étaient pas dans la colonne.
La chaîne collée ne pouvait donc jamais être un sous-texte → « Aucune correspondance ».
**C'est une normalisation de libellé (bis/ter + suffixe CP·commune + tiret/virgule), pas un trou de
données** : la parcelle existe bien dans `adresses` (`1 bis Chemin de la Citerne` = **97411000BZ1288**).

**Couverture (confirmée, pas un extrait).** La recherche tape la **table BAN entière** `adresses`,
filtre `idu IS NOT NULL AND geom IS NOT NULL`, **aucune restriction de commune/sous-ensemble** :
**339 894 adresses servables sur les 24 communes**, rattachées à **227 679 parcelles distinctes**.
Nuance à connaître : sur **431 663** parcelles au total, seules **~227 679 portent une adresse postale**
BAN ; les ~204 000 restantes (foncier non adressé — agricole, non bâti) **n'ont pas d'adresse à taper**
et se retrouvent par IDU / référence cadastrale, pas par adresse. Le trou éventuel est donc côté
*données BAN* (une parcelle sans adresse n'en a pas), pas côté périmètre de la recherche.

**Correction.** Texte cherché **élargi** à `numéro+rep+voie+CP+commune` (même ordre que la fiche) et
**séparateurs normalisés** (espaces multiples nés d'un rep vide, virgule, tiret → une espace) des DEUX
côtés (colonne ET aiguille). Nouveaux helpers `ADRESSE_SUGGEST_EXPR`, `sql_plie_lit_suggest`,
`plie_suggest` (`src/labuse/constants.py`), `_sugg_adresse` recâblé, **index GIN trigram étendu**
`ix_adresses_suggest_full_trgm` (`ensure_index`) pour rester sous le budget < 150 ms
(mesuré **4–29 ms**, Bitmap Index Scan). Le jumeau `/adresses/autocomplete` n'a **plus aucun appelant
front** (code mort) → laissé tel quel.

**Test de preuve — 3 adresses de fiches recopiées (dont celle du mandat) :**

| adresse collée (format fiche) | parcelle attendue | retrouvée |
|---|---|---|
| `1 bis Chemin de la Citerne, 97417 Saint-Denis` | 97411000BZ1288 | ✅ |
| `53 bis Rue du Cardinal, 97430 Le Tampon` | 97422000CS0802 | ✅ |
| `41 bis Chemin Jacquemin, 97470 Saint-Benoît` | 97410000BV0696 | ✅ |

Le rep discrimine correctement (« 1 bis » ne renvoie pas la parcelle « 1 » sans rep). La frappe
incrémentale (voie seule, préfixe, apostrophe/accent) reste inchangée. Régression verrouillée :
`tests/test_retours16_recherche.py::test_adresse_collee_depuis_fiche_retrouve_parcelle`.

---

## P4 — Retirer une phrase de l'encart du haut

Retiré la ligne « **49 642 localisés sur la carte · toute la profondeur Sitadel, jusqu'au 31.07.2026** »
du bloc total (`data-permis-total`). **Gardés** : le compteur « 50 544 permis autorisés en base » et la
mention « Sitadel : les permis autorisés, pas l'instruction en cours. » Variables orphelines nettoyées
(`baseLocalises`, helper `frDate`).

Captures : `captures/p4_before.png` (ligne présente) · `captures/p4_after.png` (ligne retirée).

---

## Fichiers touchés

- `frontend/src/styles/index.css` — P1 (règle chevron `.chev-boite` sur aplat).
- `frontend/src/components/outils/ModulePanel.tsx` — P2 (phrase de résultat, `onSelect`, retrait auto-ouverture) + P4 (ligne retirée, orphelins nettoyés).
- `src/labuse/constants.py` — P3 (helpers `ADRESSE_SUGGEST_EXPR` / `sql_plie_lit_suggest` / `plie_suggest`).
- `src/labuse/api/recherche.py` — P3 (`_sugg_adresse` élargi, index étendu dans `ensure_index`).
- `tests/test_retours16_recherche.py` — P3 (seed adresse `bis` + test de régression).

## Hors mandat (non touché)

Audit complet de l'outil, scoring, autres outils, exports, ingestion Sitadel, merge.
