# M140 — La liste entière sans la stocker (`feat/m140-projets`)

Branché sur `origin/main` @ `a810e018` (M138 + M139 mergés ; l'avance depuis = mon propre
M139 + du travail UI hors périmètre — signalé). Arbitrage du STOP M139 lot 3 : **la liste
complète est une requête VIVE, jamais une copie.** Trois lots. CC ne merge jamais.

**Résumé : Lot A — l'écran feuillette N (285 781) en ~28 ms/page au lieu de 9,2 s. Lot B —
CSV complet streamé (285 781 lignes en 9,2 s, 25,8 Mo, mémoire plate, zéro rang/score). Lot C —
figeage 60 → 200 (non rétroactif), en-tête réécrit pour l'état réel. Tout mesuré.**

---

## Lot A — `GET /parcelles` paginé et dégraissé

**Les DÉCIDÉES restent stockées (petites) ; les PROPOSÉES sont la liste COMPLÈTE des retenues,
servie EN DIRECT et PAGINÉE — jamais une copie, jamais tout chargé.**

- **API** (`projets.py`) — `projet_parcelles(offset, limit)` : décidées lues de `projet_parcelles`
  (toutes) ; proposées = une PAGE du cadrage vif (`_cadrage_page_idus`, `offset`/`limit`), **hors
  décidées** ; enrichissement BATCH sur la **seule page** (adresse BAN, marché, événement, carence,
  centroïde). `counts.proposee` = **total VIF restant** (pas la taille de page) ; `total_retenues`
  = N ; `page.has_more` pour feuilleter.
- **Chemin léger** — `_cadrage_page_idus` ne récupère que les **idu ordonnés** (index `rang`), sans
  l'enrichissement d'affichage lourd de `_q_v2_list` (BAN latéral, propriétaire, cluster) qu'on
  refait nous-mêmes : **2,2 s → quelques ms**. Le count complet n'est payé **qu'à la 1re page**.
- **Front** — `ProjetKanban` : fenêtre des proposées à `limit` croissant (« Charger plus · X sur N »),
  `placeholderData` anti-flicker. `moveItem` (Kanban **et** Tinder) passe aux **counts par DELTA** :
  `proposee` est le total serveur, jamais recompté depuis `.length` (une fenêtre ≠ N). Comme les
  proposées **excluent les décidées** côté serveur, décider une carte → le refetch fait remonter la
  suivante : le Tinder **parcourt naturellement les N retenues** au fil des décisions.

**Mesure (projet « toute l'île », 285 781 retenues)** :

| | Avant M140 | Après |
|---|---:|---:|
| Ouvrir l'écran | ~9,2 s (charge tout) | **517 ms** (1re page + count) |
| Feuillet suivant | — | **28 ms** |
| Feuillet profond (offset 6000) | — | 1,2 s (OFFSET est O(offset) — keyset = dette) |

L'écran **feuillette N sans jamais tout charger.** ✓

---

## Lot B — Export CSV complet, streamé, non stocké

- **API** — `GET /projets/{pid}/export.csv` → `StreamingResponse`, **curseur serveur** (`stream_results`)
  dans une **connexion propre** au générateur (la session `Depends` est fermée quand le stream se
  consomme — piège FastAPI classique, géré). Toutes les retenues du cadrage, **ordre géographique**,
  colonnes de donnée (idu, commune, section, n°, surface, adresse BAN, état du bien, SDP résiduelle,
  cause, étage 0). **SEC-IDOR** : `_projet_or_404` (autre compte → 404).
- **Doctrine** — **aucune colonne rang/score/tier** (grep colonnes = AUCUNE) ; ordre géographique,
  jamais le rang. La 1re ligne porte les **DEUX dates** comme le PDF (Lot M139-2) :
  `# cadrage figé le X · valeurs au Y (run N) · export généré le Z`.
- **Front** — bouton « CSV complet » à côté du « PDF » (extrait).

**Mesure (île complète)** : **285 781 lignes · 25,8 Mo · 9,2 s**, streamé — **mémoire plate**
(jamais matérialisé en RAM ni en base). ✓

---

## Lot C — Le figeage passe de 60 à 200

- **`config/projets.yaml`** : `shortlist_defaut: 60 → 200` (= `shortlist_max`, le mur MESURÉ :
  200 parcelles ≈ 24 pages PDF). **NON RÉTROACTIF** par construction — `shortlist_defaut` n'est lu
  qu'AU figeage : les projets déjà figés gardent leur compte (60), seuls les figeages FUTURS
  prennent 200. Vérifié : `load_yaml_config('projets')` → 200.
- **En-tête réécrit** (`pdf_projet.py`) pour l'état réel — l'ancien « Liste plafonnée » (qui
  sous-entendait, par la pirouette « élargir ne supprime pas ce rang », que la liste complète
  n'existait pas) devient :
  > « Extrait figé de {n} sur ~ {total} retenues (à ce jour) — sélectionnées par probabilité de
  > mutation (critère interne du moteur, rang non visible), présentées par ordre géographique. La
  > liste complète des retenues est consultable à l'écran (feuilletée) et en export CSV — ordre
  > géographique, aucun rang. »

  Le rang ne transite **toujours nulle part** ; la phrase est **vraie** parce que la liste complète
  existe désormais réellement (Lots A/B). L'écran porte déjà les deux dates + « X sur N ».

---

## Bricoles (M139, reste)
- `capacite_estimee` mort-lu et `q_score=None` : retirés en M139.
- **Verrou de concurrence** : toujours **dette nommée** (unicité DB + `ON CONFLICT` seuls).
- **Keyset/curseur pour l'offset profond** : `OFFSET` est O(offset) (feuillet profond 1,2 s sur
  l'île). Le feuilleter séquentiel réel reste ~28 ms ; keyset (rang) est l'optimisation future —
  **dette nommée**.

---

## Contrôles d'acceptation

1. **Pagination mesurée** : 9,2 s → 517 ms (1re) / **28 ms** (feuillet) sur l'île. ✓
2. **CSV île complet chronométré** : 285 781 lignes · 25,8 Mo · **9,2 s** streamé, mémoire plate. ✓
3. **Grep zéro score** : JSON écran = 0 rang/q_score/a_score/opportunity (`tier` = statut app
   légitime, cf. audit D) ; **CSV = 0 colonne rang/score/tier** (les hits « rang/tier » du grep
   naïf sont des sous-chaînes d'adresses : « Orangerie », « quartier »). ✓
4. **SEC-IDOR route CSV** : autre compte → 404. ✓
5. **Non-régression Lot 1** (archivage) : `DELETE` archive, cartes CRM 12 → 0 → 12, statut actif. ✓
6. **Non-régression Lot 2** (deux dates) : écran (`figee_le` + `valeurs_run`) et PDF (en-tête). ✓
7. **Non-régression PDF** : rend en 8 pages, nouvel en-tête « Extrait figé de N sur… ». ✓
8. **`tsc` vert · ruff** : `projets.py`/`pdf_projet.py` **All checks passed** (I001 pré-existants
   corrigés au passage). ✓
9. Ce rapport. ✓

*Fin. Commits sur `feat/m140-projets`. CC ne merge jamais.*
