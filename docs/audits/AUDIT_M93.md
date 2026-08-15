# AUDIT M93 — retrait du one-pager : carte de dépendances

**Mandat M93 · Phase 1 (mesure) · branche `feat/m93-retrait-onepager` · NON mergé**

Le one-pager est retiré (décision M73-B/M73 : aucune maquette de référence, palette hors
charte, aucun usage distinct du dossier/banquier). Ce document trace la frontière EXACTE
entre ce qui est **propre** au one-pager (à retirer) et ce qui est **partagé** avec les 4
autres documents (dossier, banquier, argumentaire, premium — à NE PAS toucher).

## 1. Ce qui appartient AU one-pager (à retirer)

### Backend — route (`src/labuse/api/app.py`)
La route `/parcels/{idu}/export` est **partagée** : elle sert `md | html | onepager`. On
retire le one-pager, PAS la route (md/html restent).
- `app.py:3633` — pattern `^(md|html|onepager)$` → `^(md|html)$`.
- `app.py:3635` — docstring (mention one-pager).
- `app.py:3639` — import `fiche_onepager` (à retirer de la ligne).
- `app.py:3642-3647` — la branche `if format == "onepager": …` (récup géométrie + appel).

### Backend — générateur (`src/labuse/api/export.py`)
Toutes ONEPAGER-ONLY (usages vérifiés un par un) :
- `export.py:424` — commentaire de section « One-pager (Lot D1) ».
- `export.py:426-465` — `_minimap()` (seul appelant : `fiche_onepager` L706).
- `export.py:466-714` — `fiche_onepager()` (le générateur).
- `export.py:715-721` — `_badge_class()` (seul appelant : L684, dans fiche_onepager).
- `export.py:722-732` — `_rlt_link()` (seul appelant : L707).
- `export.py:358-370` — `_eur_fourchette()` (seul appelant : L505, dans fiche_onepager).

### Backend — branche onepager dans un helper PARTAGÉ (`export_commun.py`)
`limites_document(doc)` est PARTAGÉ (4 docs) : on ne retire QUE la branche one-pager, la
fonction et son comportement pour premium/banquier/dossier restent identiques.
- `export_commun.py:86` — entrée `"onepager": []` du dict `_LIMITES_SPECIFIQUE`.
- `export_commun.py:94-95` — `if doc == "onepager": return _LIMITES_COMMUN[:3]` + mention docstring.

### Front (`frontend/src`)
Le bouton one-pager est ISOLÉ dans le menu `.exports` (pas de boucle sur 5 docs) — le
retirer ne touche pas les autres boutons (PDF premium, cadastre, SPF, pré-dossier, banquier).
- `Fiche.tsx:2372-2374` — le lien `<a data-onepager href={onePagerUrl(idu)}>{CLIENT.fiche.export.onepager}</a>`.
- `lib/api.ts:446` — `export const onePagerUrl = (idu) => …/export?format=onepager` (+ retrait de l'import dans Fiche.tsx:4 s'il devient inutilisé).
- `lib/strings.ts:410-411` — `onepager` (label) + `onepagerTip` (tooltip).

### Tests dédiés (`tests/test_lot_d.py`)
Retirer le VOLET D1 seulement (D2 comparateur / D3 filtres / 1.C bilan restent) :
- docstring L1 (mention D1), import `fiche_onepager` L7, section `# ── D1 ──` L27, et les 2
  tests `test_onepager_contient_les_sections_cles` (29-38) + `test_onepager_degrade_sans_faisabilite_ni_geom` (40-43).
- Vérifier si le fixture `_FICHE` (9-26) reste utilisé par D2/1.C → si orphelin, retirer ; sinon garder.

### Commentaires orphelins dans des fichiers PARTAGÉS (cosmétique, aucune logique touchée)
Ces fichiers ne portent que des COMMENTAIRES/docstrings citant « one-pager » comme
consommateur — à mettre à jour pour ne pas laisser d'orphelin (doctrine « ne rien laisser
d'orphelin »), sans toucher le code :
- `blocs_documents.py:6`, `pdf_premium.py:101`, `served_cascade.py:4`,
  `risques_arbitrage.py:19`, `flash/data.py:242`, `verdict_servi.py:3`.

## 2. Ce qui est PARTAGÉ (à ajuster, PAS supprimer)

### Le test des 5 documents → 4 (`tests/test_non_contradiction.py`)
Attente à ajuster (retrait voulu, pas régression — même rigueur que M91) :
- L3 docstring « CINQ documents » → QUATRE.
- L66 `op = client.get(... format=onepager ...)` → retirer.
- L67 tuple d'itération : retirer `("one-pager", op)`.
- L75 `"one-pager": op.text` → retirer.
- L126 commentaire → retirer « one-pager ».
- L140 `for name in (…, "one-pager")` → retirer.

## 3. Ce qu'il ne faut PAS toucher

- **Le profil DVF `voisinage_100m`** — le one-pager n'en est PAS le seul lecteur : consommé
  par la **fiche écran** (`app.py:2493` + `app.py:3531` → `Fiche.tsx:2108-2114`, bloc « Autour,
  à moins de 100 m ») et par `app.py:2788` (`marche_dvf(profil=DVF_VOISINAGE_100M)`). **Il reste**
  (interdit du mandat) — aucune décision de profil DVF ici.
- **Fonctions/blocs mutualisés** : `marche_service` (dont `reserve_methode`), `blocs_documents`
  (ANC/réhab), `plan_ortho`, `briques_pdf`, et dans export.py `_comparables_view`,
  `_prospection_view`, `_verdict_label`, `_m2`, `_eur`, `_eurm2`, `_today` (partagés md/html) —
  intacts.
- **La fonction `limites_document`** elle-même (seule sa branche one-pager part).
- **Les formats `md` et `html`** de la route `/export` (exports bruts, hors périmètre).

## 4. Le golden — NON concerné

Le golden (`qa/golden_check.py`) ne récupère AUCUN export (`collect_api` ne fetch que
`/parcels/{idu}` + `/v2/score/{idu}`) : il ne teste pas le one-pager. Il reste **119/119**,
inchangé par ce retrait. La couverture « 5 documents » vit uniquement dans
`test_non_contradiction`.

## 5. Outillage QA (hors code servi — à signaler)

Scripts QA citant `format=onepager` (se casseraient après retrait, mais ne sont ni servi ni
front) : `qa/m54ab_validate.py`, `qa/m54ab_regen.py`, `qa/m48/audit_grid.py`. Je propose de
mettre à jour les 2 helpers actifs (validate/regen) pour ne pas laisser d'appel mort ; les
bilans figés (m33–m48/*.md) restent l'historique. À confirmer.

## STOP — Vic valide la frontière

Résumé : retrait circonscrit à **route (1 branche) + générateur export.py (5 fns onepager-only)
+ 1 branche dans un helper partagé + front (bouton/api/strings) + test D1 + ajustement du test
5→4**. `voisinage_100m` RESTE (consommé par la fiche écran). Golden non concerné. Aucune
fonction partagée cassée. Rien de commenté « au cas où » : le code part (git garde l'historique).
