# DOCS-FIX-1 — correction des 12 points de DOCS-AUDIT-1

**Mandat de correction.** Le back est sain (DOCS-AUDIT-1 : 0 chiffre faux, écran = PDF 4/4, recette
exports VERTE, cloison prouvée). Ce mandat corrige **le branchement et les libellés, rien d'autre**.

- Branche `fix/docs-fix-1` depuis `origin/main` (`8ec472c0`) · worktree `~/Desktop/labuse-docsfix`
  · ports API **8709** / Vite **5909** · venv `~/Desktop/labuse/.venv` + `PYTHONPATH=…/labuse-docsfix/src`.
- Témoins : `97415000AM0097` (Saint-Paul, **zone N**, exclue — forêt domaniale) · `97411000BZ1065`
  (Saint-Denis, **Uh**) · `97416000ES0981` (Saint-Pierre, **Ug**).
- **Aucun run, aucun recalcul, aucun paiement réel, aucune bascule.** Arrêt propre, ports libérés.

> **Résultat.** Les 12 points sont traités (10 corrigés dans le code, P8 tranché « décision produit »,
> P10 par l'arbitrage Vic). Les 4 arbitrages de Vic priment et sont appliqués tels quels. Frontend
> `tsc` 0 / **239 vitest** (235 existants + 4 nouveaux) / build OK. Backend : garde-fou proxy 3/3,
> écran=PDF 4/4, cloison 2/2, comparatif `test_lot_d` 5/5, **recette exports VERTE** (0 divergence,
> 0 mot interdit). Constat navigateur réel pour P1/P2/P3/P5/P9/P11/P12. **0 texte client ne dit plus
> « Financier ».**

---

## Tableau P1 → P12

| # | Gravité (audit) | Fait | Correctif (fichier:ligne) | Constat / capture |
|---|---|---|---|---|
| **P1** | bloquant (dev) | ✅ | `frontend/vite.config.ts` — ajout de `/gabarit`, `/comparatif`, `/etude-zone`, `/documents` aux `apiPaths` **+ `/config`, `/partners`, `/vocabulaire`** (trois trous dev pré-existants révélés par le garde-fou). **Garde-fou** : `tests/test_proxy_dev_couvre_routes_api.py` (échoue si une route d'API n'est ni proxifiée ni allowlistée). | avant `captures/avant/P1-gabarit-dev-404.png` (404) → après `captures/apres/P1-gabarit-dev-pdf-ok.png` (PDF rendu en dev). 7 routes testées via le proxy :5909 = **200** (voir §Lot 1). |
| **P2** | faux (client) | ✅ | « Financier » → « Bilan » partout côté client : `exports/miroir.py:687,1004`, `exports/blocs/bilan.py:21`, `api/projets.py:1566` (détail 410) ; front `FinancierQuestionnaire.tsx` (eyebrow `BILAN` + 3 messages), `CalculetteFonciere.tsx:49`, `constructibilite.tsx:153`. Clé/route/table `financier` **inchangées**. | PDF Dossier : « document **Bilan** » ×2 (`pdftotext`). Eyebrow avant `P2-…-financier.png` → après `P2-…-bilan.png`. Scan des 7 PDF témoins : **0** occurrence du document « Financier » (seul « Portage **financier** » = l'adjectif, légitime). |
| **P3** | gênant (UX) | ✅ | `frontend/src/lib/ouvrirDocument.ts` (hook `useOuvrirDocument`, repris du Bilan) : état d'attente `enCours` → le bouton affiche « Génération… » / la tuile « … », l'app ne fige pas. Branché dans `DocumentsView.tsx` (porte) et `Fiche.tsx` (tuiles). | `captures/apres/P3-generation-en-cours.png` (bouton « Génération… »). Blobs ouverts proprement (gabarit/comparatif/pré-dossier/dossier-fiche), jamais d'onglet blanc. |
| **P4** | gênant (UX) | ✅ | Même hook : `fetch` → sur 404/422/500 un **message FR lisible** (inline dans la porte, toast ailleurs), jamais de JSON brut ; 422 **nomme les manques** (comme le Bilan). Verrou `frontend/src/lib/ouvrirDocument.test.tsx` (4 cas). | `ouvrirDocument.test.tsx` 4/4 (200 ouvre un blob ; 422/404/500 → message FR + aucun onglet). |
| **P5** | trompeur | ✅ | `api/app.py` `compare()` : repli `zone_dominante(db, pid)` quand `fiche_payload.zone` est None (parcelle exclue) → la Zone PLU du Comparatif = celle de la fiche. `exports/blocs/comparatif.py:60` : si aucune zone PLU, « **hors zonage PLU** » (raison en clair), jamais « — ». | avant `pdftotext` : `Zone PLU … — Uh Ug` → après : `Zone PLU … **N** Uh Ug`. `captures/apres/P5-comparatif-zone-N.png`. |
| **P6** | gênant | ✅ | `DocumentsView.tsx` `LigneDoc` : bouton **« Supprimer »** (ton `danger`, deux temps Supprimer → Confirmer) appelant `supprimerDocument` (route `DELETE` + client existaient, aucun bouton ne les appelait). | Cycle write→état→suppression→cloison prouvé par `test_documents_bibliotheque_cloison` 2/2. En dev local (auth désactivée) la bibliothèque reste vide par conception (voir §Note auth). |
| **P7** | gênant | ✅ | Le Bilan n'est plus inscrit à l'**ouverture** de l'écran d'hypothèses : `DocumentsView.tsx` passe `onGenerated` à `FinancierQuestionnaire`, qui l'appelle **après génération réelle** du PDF (`FinancierQuestionnaire.tsx` `ouvrirDoc`). Plus d'entrée « fantôme » qui renverrait 422. | Code + revue. |
| **P8** | cosmétique | ✅ (décision produit) | **Accepté** : chaque génération = une ligne d'**historique** daté (instantané de millésimes figé → état « À jour / Sources modifiées »). P7 supprime le seul doublon trompeur (le Bilan fantôme). Pas d'upsert : l'historique est voulu. | Documenté ici. |
| **P9** | faux (client) | ✅ | `DocumentsView.tsx:383` — « Huit documents » → « **Sept** documents ». | avant `P9-page-docs-huit.png` → après `P9-page-docs-sept.png`. |
| **P10** | arbitrage | ✅ (arbitrage Vic 1) | **Courrier n'est pas un document** (c'est un outil, il part d'une parcelle) → pas de 8ᵉ tuile (le catalogue a 7 tuiles, inchangé) ; l'intro dit « Sept documents » (P9). | Catalogue à 7 tuiles (capture page Docs). |
| **P11** | cosmétique | ✅ | `Fiche.tsx` : les tuiles Dossier/Apporteur/Pré-dossier ne sont plus des `<a href>` littéraux mais des boutons qui passent par les **builders encodés** `docDossierUrl`/`docApporteurUrl`/`docPreDossierUrl` + le hook d'ouverture propre. | Tuiles = `<button>` (vérifié DOM) ; Dossier depuis la fiche ouvre un blob PDF. |
| **P12** | cosmétique | ✅ | `catalogue.ts` — badge « Excel » **retiré** du Bilan (`formats: ['PDF']`) tant que l'export n'existe pas (`_EXCEL_DISPONIBLE` vide). La plomberie `r.excel`/bouton Excel de `LigneDoc` reste en place. | Carte Bilan : badges = `['PDF']` seul (vérifié DOM + capture page Docs). |

---

## Arbitrages de Vic appliqués

1. **Courrier n'est pas un document** → pas de tuile, intro « Sept documents » (P9/P10).
2. **« Financier » disparaît côté client** → « Bilan » partout (prose Dossier ×2, `miroir.py`, `blocs/bilan.py`,
   détail 410 `projets.py`, eyebrow + messages du questionnaire, Calculette, taxe/constructibilité).
   Clé interne / route `/financier` / table / préfixe `FI-` / attributs `data-financier-*` **inchangés**.
3. **Comparatif, zone PLU** → lit `zone_servie.zone_dominante` (même zone que la fiche) ; raison en clair
   (« hors zonage PLU ») plutôt qu'un tiret si aucune zone ne couvre la parcelle.
4. **P1 prioritaire** → proxy comblé **et** garde-fou posé (4ᵉ occurrence impossible sans faire échouer un test).

---

## Lot 1 — plomberie (P1)

Routes testées **via le proxy Vite dev (:5909)** — toutes 404 avant, 200 après :

| route | avant | après |
|---|---|---|
| `/gabarit/{idu}.pdf` | 404 | **200** application/pdf |
| `/comparatif.pdf?idus=…` | 404 | **200** application/pdf |
| `/etude-zone.pdf?idu=…` | 404 | **200** application/pdf |
| `/documents?limite=…` | 404 | **200** application/json |
| `/config/run` | (404 silencieux) | **200** application/json |
| `/vocabulaire/paliers` | (404 silencieux) | **200** application/json |
| `/partners/profiles` | (404 silencieux) | **200** application/json |

**Garde-fou** (`tests/test_proxy_dev_couvre_routes_api.py`, 3/3) : lit les routes de `app.routes`, mime le
match-préfixe de Vite, et échoue si une route n'est ni dans `apiPaths` ni dans l'allowlist documentée
`NON_PROXIFIE` (pages rendues par le serveur, auto-doc FastAPI, webhooks). Un 3ᵉ test vérifie que
l'allowlist n'a pas d'entrée morte.

---

## Recette

- **Génération des 7 documents sur les 3 témoins (page Docs), 0 erreur** :

| doc | AM0097 (N) | BZ1065 (Uh) | ES0981 (Ug) |
|---|---|---|---|
| Dossier | 200 | 200 | 200 |
| Bilan | 200 | 200 | 200 |
| Apporteur | 200 | 200 | 200 |
| Pré-dossier PC | **200** (1,45 Mo, ~80 s à froid — tuiles ortho) | 200 (1,34 Mo) | 200 (1,51 Mo) |
| Gabarit | **422 attendu** (zone N non constructible — comportement voulu) | 200 | 200 |
| Étude de zone | 200 | 200 | 200 |
| Comparatif | 200 (paires + triple des 3 témoins = 3 combinaisons) | | |

  → 0 erreur. Les 422 (Gabarit zone N ; Bilan sans questionnaire) sont des **comportements voulus**.
  ⚠ Pré-dossier AM0097 ≈ 80 s à froid (fetch des tuiles ortho du plan de situation, `plan_ortho`
  timeout 10 s/tuile, auto-guéri par le cache tuiles — cf. CHASSE-2) : **hors périmètre** (DOCS-FIX-1 ne
  touche ni `pre_dossier.py` ni `plan_situation.py`) ; l'audit l'avait mesuré à 23,6 s à chaud.

- **Depuis la fiche** : les tuiles-documents (Dossier · Bilan · Apporteur · Pré-dossier) sont désormais
  des boutons passant par le hook d'ouverture propre ; constat réel : le Dossier depuis la fiche BZ1065
  ouvre un blob PDF. ℹ️ La fiche n'expose que **4** tuiles-documents (DOCS-AUDIT-1 §1.2) ; Gabarit /
  Comparatif / Étude de zone vivent uniquement sur la page Docs — « 21 + 21 » n'est donc pas littéral
  (21 depuis la page Docs ; 4 familles × 3 depuis la fiche).

- **Recette exports (`scripts/recette_exports1.py`) : VERTE** — 0 divergence, 0 mot interdit (Dossier /
  Apporteur / Bilan / Gabarit / Comparatif / Étude de zone).

- **grep final « Financier » côté client** : scan `pdftotext` des 7 PDF des 3 témoins → **0** occurrence
  du **document** « Financier » (seul « Portage financier » subsiste = l'adjectif « financier »,
  légitime). Front : les seules occurrences restantes de « Financier » sont des **commentaires** JSX /
  TS et une description **admin** (`admin/circuit/Detail.tsx:249`, opérateur, hors périmètre client).

### Note — bibliothèque « Mes documents » en dev local

En `LABUSE_ENV=local`, l'authentification est **désactivée** → la session n'a pas de compte
(`current_compte` = None) : `GET /documents` répond 200 (liste vide) et `POST /documents` répond 401
**par conception** (écriture réservée à un compte, `compte_ou_401`). Le cycle complet (écriture →
apparition → état « À jour » → cloison inter-comptes) est prouvé par `test_documents_bibliotheque_cloison`
(2/2, compte réel via TestClient). La correction P1 rend bien `GET /documents` joignable en dev (200,
était 404).

---

## Vérifications

| vérif | résultat |
|---|---|
| `tsc -b` (front) | 0 erreur |
| `vitest run` | **239** passés (235 + `ouvrirDocument.test.tsx` 4) |
| `test_proxy_dev_couvre_routes_api.py` | 3/3 |
| `test_docs1_ecran_egale_pdf.py` | 4/4 |
| `test_documents_bibliotheque_cloison.py` | 2/2 |
| `test_lot_d.py` (comparatif) | 5/5 |
| recette exports | **VERTE** |

---

## Commits

- **DOCS-FIX-1 Lot 1** — proxy Vite (P1) + garde-fou.
- **DOCS-FIX-1 Lot 2** — libellés client (P2 Financier→Bilan, P5 zone Comparatif, P9 « Sept », P12 badge Excel).
- **DOCS-FIX-1 Lot 3** — ouverture propre des documents (P3/P4), supprimer (P6), inscription après génération
  (P7), tuiles fiche via builders (P11) + livrable.
