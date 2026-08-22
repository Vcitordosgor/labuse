# Audit — outil « Comparer des parcelles » (A8). CONSTAT SEUL, aucune correction.

Endpoint `GET /compare?idus=…` (`app.py:4236`) → `_compare_row(_build_fiche(…))` (`app.py:4247`).
Front `frontend/src/components/compare/ComparePanel.tsx`. Mesuré sur run servi `q_v10_m129`.

## VERDICT EN UNE LIGNE
Le comparateur passe par la fiche **LEGACY `_build_fiche`**, pas par `_q_v2_fiche` (la premium
servie). Conséquence mesurée : **le verdict côte à côte est DÉGRADÉ** — `tier_v2`/`rang_v2`/
`etage0` sortent toujours à `None`, donc la puce M137 n'apparaît jamais (elle retombe sur
« Classement historique » gris, ou « — »), le **rang n'est jamais affiché**, et **ni la fraction
ni la raison dominante M135** ne sont dans la comparaison. Pas de défaut de *donnée* (tout est
scopé au run servi, « — » honnête partout, pas d'export) — un défaut de **restitution** : la
comparaison ne parle pas le vocabulaire M135/M137 de la fiche.

---

## 1. Branchement et données

**Tables lues** (toutes via `_build_fiche`, `app.py:3619`) :
- `dryrun_cascade_results WHERE run_label = Q_A_RUN_LABEL` (`app.py:3636`) → **scopé q_v10_m129 ✓**
  (contraintes, contrainte majeure). Le rail legacy `cascade_results` est mort (M73).
- verdict : `verdict_servi(db, idu)` (`app.py:3695`) → tier/rang/label/statut **du run servi ✓**.
- faisabilité / résiduel / bilan : caches parcelle (via `_build_fiche`).
- `terrain_zone_eur_m2` : `build_marche_commune` → `prix_terrain_nu_par_zone` (M79), médiane **de
  zone** (`app.py:4259-4263`).
- **`opportunity_score` / `completeness_score` : `ev = _latest_eval(db, p.id)` (`app.py:3624`)** —
  `parcel_evaluations ORDER BY evaluated_at DESC LIMIT 1`, **NON scopé au run servi** (dernière
  éval, quel que soit le run).

**Scoping q_v10_m129** : OUI pour cascade + verdict + faisabilité. **NON** pour
`opportunity_score`/`completeness_score` (rail v1 `parcel_evaluations`, dernière éval libre).

**Vestiges de matrice** :
- `q_score`, `a_score`, `matrice_statut`, `a_completude` : **ABSENTS par nom** de `_compare_row`
  et du front ✓ (contrairement à d'autres outils de la semaine).
- MAIS `opportunity_score` + `completeness_score` (les 2 notes de la **matrice v1**,
  `parcel_evaluations`) sont **encore récupérés** (`_compare_row`, `app.py:4057-4058`), non scopés,
  et **jamais affichés** par le front (absents de `ROWS`) → **charge morte** dans le payload.
- Symétrique : `_compare_row` LIT `tier_v2`/`etage0`/`rang_v2` (`app.py:4056`) que
  `_build_fiche` **n'écrit jamais** (son `verdict_block`, `app.py:3696-3714`, porte `tier`/`rang`/
  `label`, pas `tier_v2`) → ces 3 champs sont **toujours `None`** (vérifié sur 2 parcelles réelles :
  `97411000DE0285` reserve_fonciere, `97415000DK1044` chaude → tier_v2=None, rang_v2=None).

**LIMIT caché** : NON de caché. Cap **explicite à 3** (`ids[…][:3]`, `app.py:4241`, documenté
« 2 à 3 »). `_compare_row` tronque le détail à **4 contraintes** (`contraintes[:4]`, `app.py:4068`)
mais `n_contraintes` sert le compte VRAI → pas de troncature muette.

**Test « ne lève pas »** : NON, pas de vrai. `tests/test_lot_d.py:27`
`test_compare_row_extrait_les_champs_alignes` teste `_compare_row` sur un **FICHE FABRIQUÉ**
(`_FICHE`, `status="opportunite"`, SANS `tier_v2`) qui **ne correspond pas** à la sortie réelle de
`_build_fiche` (status = code de tier, verdict_servi) → il **masque** le bug tier_v2=None. Aucun
test n'appelle `_build_fiche` ni l'endpoint `/compare` sur une parcelle réelle.

## 2. Ce qu'il compare

**Critères AFFICHÉS** (`ComparePanel.tsx:20-28` + en-tête) :
en-tête = puce verdict + commune (+ rang) ; lignes = **Surface · Zone PLU · Constructible ·
SDP max estimée · Charge foncière /m² · Prix terrain nu zone · Contrainte majeure** + « Détail
contraintes » (liste, max 4).

**À jour du vocabulaire M135/M137 ? NON — c'est le défaut central :**
- **Puce de tier** (`ComparePanel.tsx:14-16, 101`) : `verdictMeta(status, tier_v2, etage0)` avec
  `tier_v2`/`etage0` **toujours None** → `verdictMeta` (status.ts) retombe sur le repli legacy :
  `chaude` → **« Classement historique » (gris neutre)** ; `reserve_fonciere` (absent de
  `STATUT_META`) → **« — »**. **Jamais** la puce d'action M137 (« À suivre », « Long terme »…).
- **Rang** (`ComparePanel.tsx:102`) : gated sur `r.rang_v2 != null` → **jamais affiché** (None).
- **Fraction M135** (« 1/5 sous 1 an ») : **ABSENTE** de la comparaison.
- **Raison dominante M135** : **ABSENTE** de la comparaison.

**Critères que la fiche affiche mais que la comparaison ignore** (candidats d'ajout, source) :
- la **puce d'action + le rang** corrects → `verdict_servi` / `_q_v2_fiche` (déjà calculés).
- la **fraction** de probabilité (« 1/5 sous 1 an ») → `_q_v2_fiche` (M135).
- la **raison dominante** → `_q_v2_fiche` / `reasons` (M135).
- résiduel (**SDP résiduelle**, **sous-densité**, **taux d'emprise**) et **CA fourchette** : déjà
  DANS le payload `_compare_row` (`sdp_residuelle_m2`, `sous_densite`, `taux_emprise_pct`,
  `ca_bas`/`ca_haut`) mais **non affichés** par `ROWS` — à exposer sans requête supplémentaire.
- proprietaire moral (PM) : sur la fiche (`_q_v2_fiche.proprietaire_moral`), absent du comparateur.

**Critère faux/trompeur ?**
- Le vrai piège est la **puce de verdict** : « Classement historique »/« — » LAISSE CROIRE qu'il
  n'y a pas de classement vivant, alors que la parcelle EST classée au run servi. Trompeur.
- « Prix terrain nu zone » = médiane **de la zone** (M79), pas le prix de CETTE parcelle — le
  libellé dit « zone », donc honnête, mais à ne pas lire comme un prix parcellaire.
- Pas de « prix bâti déguisé en prix terrain » (le motif M137-R) trouvé ici : le comparateur ne
  sert pas de prix probable foncier parcellaire.

## 3. Ergonomie

- **Combien** : **3 max** (`app.py:4241` `[:3]` ; front « /3 » `ComparePanel.tsx:45,73`).
- **Comment ajouter** : (1) **fiche → porte « Comparer »** (`Fiche.tsx:2207-2209`,
  `addToCompare(idu)` + ouverture) ; (2) **clic carte** en mode picking (`ComparePanel.tsx:41-66`,
  surligne via `moduleMap`). **PAS depuis un projet / le kanban** (aucun point d'entrée).
- **Donnée manquante** : **« — » partout** (les `val()` de `ROWS` renvoient `'—'` sur `null`) —
  **aucun zéro inventé ✓**. (`opportunity_score` peut valoir 0 dans le payload mais n'est pas
  affiché.)
- **Export** : **AUCUN** (ni PDF ni CSV — pas de bouton d'export dans `ComparePanel`).
- **Freins à l'usage (lecture du code)** :
  1. **Verdict dégradé** — la première chose lue (la puce) est fausse/muette (« Classement
     historique »/« — ») pour toutes les parcelles → l'outil paraît « hors run ».
  2. **Rang jamais affiché** (rang_v2 None) — on compare sans le classement.
  3. **Ni fraction ni raison M135** — la comparaison est plus pauvre que la fiche.
  4. **Pas d'export** — on ne peut pas emporter la comparaison (banquier, associé).
  5. **Pas d'ajout depuis un projet** — le geste naturel (comparer 3 parcelles d'une shortlist)
     n'existe pas ; il faut ouvrir chaque fiche ou cliquer la carte.
  6. **Payload à moitié mort** — résiduel / CA / opportunity / completeness transités mais non
     montrés ; opportunity/completeness en plus non scopés au run.

## Cause racine unique
Le comparateur consomme **`_build_fiche` (legacy)** au lieu de **`_q_v2_fiche` (premium servie)**.
La fiche à l'écran est correcte (elle, passe par `_q_v2_fiche`, `app.py:3185`) ; le comparateur,
lui, lit une forme de verdict qui n'a plus les clés v2 → tout le reste (puce, rang, fraction,
raison) en découle. Corriger la source (ou aligner `_compare_row` sur `verdict_servi`/`_q_v2_fiche`)
règle §2 d'un coup. À arbitrer par Vic.
