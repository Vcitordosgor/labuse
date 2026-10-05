# DOCS-AUDIT-1 — la page « Docs » : tout est là, tout est branché, tout dit vrai ?

**Audit en lecture seule.** Aucune correction : on liste, Vic tranche, un mandat DOCS-FIX-1 suivra.

- Branche `audit/docs-audit-1` depuis `origin/main` · worktree `~/Desktop/labuse-docsaudit` · ports API **8708** / Vite **5908** (base `/socle/`).
- Env PDF : `.venv` du dépôt (`~/Desktop/labuse/.venv`, WeasyPrint 70.0 OK), `LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse`, `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`, `PROJ_DATA=…/labusedb/share/proj`. **Aucun commit de code, aucun run, aucun recalcul, aucun mail, aucun paiement réel** (le Flash n'a pas été déclenché ; seule la livraison Dossier a été exercée, cf. §2).
- Témoins : `97415000AM0097` (Saint-Paul, **zone N**, bâti, parcelle *exclue* — forêt domaniale) · `97411000BZ1065` (Saint-Denis, **Uh**, bâti, 3 Chemin de la Citerne) · `97416000ES0981` (Saint-Pierre, **Ug**, bâti, 113 av. du Général de Gaulle).
- Livrables : ce rapport + `pdf/` (19 documents générés sur les 3 témoins) + `captures/` (3 PNG).

> **Verdict d'ensemble.** La chaîne de génération est **saine côté back** : les 7 documents se produisent sur les témoins, les chiffres sont cohérents (fiche = PDF = PDF), 0 mot interdit, 0 page blanche, dates et décimales françaises, verrou écran=PDF **vert (4/4)**, recette exports **VERTE** (0 divergence), cloison par compte **prouvée**. **Zéro faux numérique.**
> Les problèmes sont **de branchement et de libellé**, pas de calcul : (1) en `npm run dev` le proxy Vite ne route pas 4 routes DOCS-1 → **Gabarit / Comparatif / Étude de zone et toute la bibliothèque « Mes documents » sont cassés en dev** (prod Caddy épargnée) ; (2) le **Dossier dit « le document Financier »** alors que le document s'appelle **« Bilan »** côté client ; (3) l'intro annonce **« Huit documents »** pour **7 tuiles** et **« Courrier » n'est pas sur la page Docs** ; (4) les documents ouverts par `window.open` n'ont **aucune gestion d'erreur ni spinner** (JSON brut / onglet blanc 15–24 s) ; (5) le **Comparatif affiche « — » en Zone PLU** pour une parcelle que la fiche dit « N ».

---

## Les 5 problèmes les plus graves

| # | Gravité | Document | En un mot |
|---|---|---|---|
| 1 | **Bloquant (dev) / sain en prod** | Gabarit · Comparatif · Étude de zone · Mes documents | Proxy Vite incomplet : en `npm run dev`, ces 4 routes tombent sur une page d'erreur Vite / 404 au lieu du PDF ou de la liste. Caddy (prod) route tout → prod OK. |
| 2 | **Faux (client)** | Dossier | Le Dossier renvoie « le document **Financier** » (×2) — ce document s'appelle **« Bilan »** partout ailleurs côté client. Nom fantôme. |
| 3 | **Gênant (UX)** | tous (sauf Bilan & Gabarit) | Documents ouverts par `window.open` : sur 404/422/500 l'onglet affiche le **JSON brut** ; pendant 15–24 s de génération, **onglet blanc, aucun spinner**. |
| 4 | **Trompeur** | Comparatif | Ligne « Zone PLU » = **« — »** (marquée *sourcé*) pour St-Paul alors que fiche + Dossier + Apporteur disent **« N »**. |
| 5 | **Faux (client)** | page Docs | L'intro dit **« Huit documents »** ; **7 tuiles** affichées. Et « Courrier » (annoncé au mandat) **n'est pas** sur la page Docs. |

---

## 1. Inventaire

### 1.1 Tuiles de la page Docs (`frontend/src/components/documents/catalogue.ts`)

La grille affiche **7 tuiles** (toutes cliquables, aucune grisée ; « Comparables DVF » retiré par RECETTE-2). Route de génération résolue dans `frontend/src/lib/api.ts`.

| Tuile | Présent | Libellé carte | kind | Route de génération | fichier:ligne |
|---|---|---|---|---|---|
| Dossier | oui | Dossier · PDF | parcelle | `GET /dossier/{idu}.pdf` | api.ts:1190 → `dossier.py:64` |
| Bilan | oui | Bilan · PDF · Excel | parcelle | écran d'hypothèses → `GET /financier/{idu}.pdf` | DocumentsView.tsx:176 ; api.ts:1191 → `documents.py:96` |
| Apporteur | oui | Apporteur · PDF | parcelle | `GET /apporteur/{idu}.pdf` | api.ts:1192 → `documents.py:101` |
| Pré-dossier PC | oui | Pré-dossier PC · PDF | parcelle | `GET /pre-dossier/{idu}.zip` | api.ts:1193 → `pre_dossier.py:1026` |
| Gabarit | oui | Gabarit · PDF | parcelle | `GET /gabarit/{idu}.pdf` | api.ts:1194 → `documents.py:128` |
| Comparatif | oui | Comparatif · PDF | multi (2–3) | `GET /comparatif.pdf?idus=` | api.ts:1195 → `documents.py:150` |
| Étude de zone | oui | Étude de zone · PDF | zone (rayon) | `GET /etude-zone.pdf?idu=&rayon_km=` | api.ts:1197 → `documents.py:173` |

Le **PDF Excel du Bilan n'existe pas** : `_EXCEL_DISPONIBLE = set()` (documents_bibliotheque.py:44) → le badge « Excel » de la carte et le filtre sont affichés, mais aucune ligne de bibliothèque ne proposera jamais le bouton Excel. Badge trompeur (cosmétique, cf. P12).

### 1.2 Boutons du bas de fiche (`frontend/src/components/fiche/Fiche.tsx`, `GrilleOutils` l.1957)

6 tuiles : **4 documents** + 2 outils.

| Tuile fiche | Libellé | Route / action | fichier:ligne | Même route que la page Docs ? |
|---|---|---|---|---|
| Dossier | Dossier | `href=/dossier/{idu}.pdf` (+ quota /dossier/statut) | Fiche.tsx:2033 | **oui** (idem Docs) |
| Finance | **Bilan** (`CLIENT.fiche.export.finance`) | ouvre `FinancierQuestionnaire` → `GET /financier/{idu}.pdf` | Fiche.tsx:2067,2069 ; FinancierQuestionnaire.tsx:198 | **oui** (même écran, même route) |
| Apporteur | Apporteur | `href=/apporteur/{idu}.pdf` (littéral) | Fiche.tsx:1961 | **oui** (URL littérale non encodée vs builder encodé — même route, cf. P11) |
| Pré-dossier PC | Pré-dossier PC | `href=/pre-dossier/{idu}.zip` (grisé hors plan Intégral) | Fiche.tsx:2051 ; gate 2044 | **oui** |
| Courrier | Courrier | `setCourrierPrefill(idu); setModule('courriers')` → module client | Fiche.tsx:1964 | — (outil, pas sur page Docs) |
| Remonter le temps | Remonter le temps | `setModule('temps')` | Fiche.tsx:1970 | — (outil) |

**Gabarit / Comparatif / Étude de zone ne sont PAS des boutons de bas de fiche** : ils sont exclusivement sur la page Docs (le Gabarit est aussi accessible via le tiroir Constructibilité « Ouvrir le Gabarit » — qui ouvre l'**outil**, pas le PDF).

### 1.3 Documents en trop / en double / manquants / au nom incohérent

- **« Courrier » absent de la page Docs.** Le mandat le liste comme 8ᵉ document ; dans le produit c'est un **outil** (relance propriétaire : aperçu PDF `POST /courrier/pdf`, **aucun envoi** côté client — l'envoi est un geste admin). Il n'a pas de tuile au catalogue. → **arbitrage Vic** (§Questions).
- **Nom interne `financier` vs libellé `Bilan`.** La route (`/financier`), la clé builder, le préfixe de numéro (`FI-…`) et la clé questionnaire restent `financier` ; le libellé client est « Bilan » (catalogue, `strings.finance`, `builder._LABEL["financier"]="Bilan"`). Couture interne **assumée et sans impact** — **sauf** la fuite du mot « Financier » dans le Dossier (cf. **P2**).
- Le numéro imprimé du Bilan est `FI-AAAAMMJJ-xxxx` (préfixe `FI`) : visible en tête du PDF (« FI-20261005-1065 »). Référence technique, pas un libellé de document — acceptable, mais à savoir.

---

## 2. Génération sur les 3 témoins

**Back direct (API :8708)** — chaque route appelée au curl, PDF/ZIP enregistrés dans `pdf/`.

| Document | St-Paul N | St-Denis Uh | St-Pierre Ug | pages | notes |
|---|---|---|---|---|---|
| Dossier | 200 · 14,9 s* · 9 p | 200 · 3,2 s · 10 p | 200 · 10 p | 9–10 | *cold start (tuiles) ; chaud ~3 s |
| Bilan (GET nu) | **422** | **422** | **422** | — | *document_non_etablissable* : il manque programme + régime TVA (voulu) |
| Bilan (questionnaire rempli) | 200 · 4 p | 200 · 4 p | 200 · 5 p | 4–5 | PUT `/financier/{idu}/questionnaire` puis GET → OK |
| Apporteur | 200 · 1,4 s · 4 p | 200 · 2,0 s · 4 p | 200 · 4 p | 4 | |
| Pré-dossier PC (.zip) | 200 · **23,6 s** · 8 pièces | 200 · **18,2 s** · 8 pièces | 200 · 8 pièces | — | CERFA 13406*17 (maison indiv.), millésime vérifié 21/08/2026 ; checklist honnête |
| Gabarit | **422** (zone N, bloqué) | 200 · 0,4 s · 2 p | 200 · 2 p | 2 | 422 attendu : « donnée réglementaire manquante » |
| Étude de zone (r=2) | 200 · 6,5 s · 2 p | 200 · 4,1 s · 3 p | 200 · 3 p | 2–3 | carte ortho IGN en page 1 OK |
| Comparatif (2 / 3 parc.) | 200 · 2 p / 200 · 2 p | — | — | 2 | paysage, 17 lignes |

**Parcelle hors run servi** (`97411000ZZ9999`, `…AM0097X`) : `GET /dossier/*.pdf` → **404** `{"detail":"Parcelle … inconnue de l'analyse en cours."}` — 404 propre côté back (mais rendu brut côté client, cf. P4).

**Front (navigateur :5908)** — testé via Playwright sur BZ1065 depuis la page Docs ET depuis la fiche :

- **Fenêtre (porte)** : saisie adresse/IDU/référence + autocomplétion OK ; parcelle résolue affiche IDU + adresse + `U · 1 625 m²` ; Comparatif à 2–3 entrées ; Étude de zone avec rayon −/+ (1..20, défaut 2) ; Bilan → écran d'hypothèses `FinancierQuestionnaire`.
- **Dossier / Apporteur / Pré-dossier / Bilan** (routes proxifiées) : **ouverture PDF réelle en dev** (capture `02-dossier-pdf-dev-ok.png`).
- **Gabarit / Comparatif / Étude de zone** (routes **non** proxifiées) : l'onglet ouvert par `window.open('/gabarit/…​.pdf')` tombe sur la page d'erreur Vite **« public base URL of /socle/… »**, HTTP **404** (capture `03-gabarit-dev-404.png`). **Le back fonctionne** (cf. tableau ci-dessus) — c'est un trou de proxy dev (cf. **P1**).
- **Gabarit porte, pré-contrôle** : sur St-Paul (zone N), la fenêtre interroge `/outils/gabarit` (proxifié) et affiche **« Gabarit non calculable sur cette parcelle : donnée réglementaire manquante »**, bouton désactivé. **Bonne** gestion d'erreur côté client (l'exception du lot).

---

## 3. Branchement — la donnée est-elle juste ?

- **`scripts/recette_exports1.py`** (successeur, `verifier_docs1` inclus) : commentaires encore datés « Résumé » mais la suppression est gérée. **Joué → RECETTE VERTE** : 0 divergence, **0 mot interdit** sur Dossier/Apporteur/Bilan/Gabarit/Comparatif/Étude de zone (témoins propres BO0852/AD0554/DY0106/AV0110 + BZ1065).
- **Verrou écran=PDF (V5d/V5f/Z5, `tests/test_docs1_ecran_egale_pdf.py`)** : **4/4 verts** (fuites==[], refus zone A/N, valeurs ancrées gabarit/sdp/population identiques écran↔PDF).
- **Cloison (`tests/test_documents_bibliotheque_cloison.py`)** : **2/2 verts** (compte A voit / compte B 404 ; état À jour→modifié→À jour).

**20 chiffres clés, fiche écran = PDF = PDF entre eux** (vérif croisée Dossier / Apporteur / Bilan / Gabarit / Comparatif / Étude de zone) :

| # | Donnée | Témoin | Valeur servie (fiche) | PDF(s) | Verdict |
|---|---|---|---|---|---|
| 1 | Surface | St-Denis | 1 625 m² | Dossier=Apporteur=Bilan=Comparatif `1 625 m²` | ✅ |
| 2 | Surface | St-Paul | 1 620 m² | Dossier=Apporteur=Bilan=Comparatif `1 620 m²` | ✅ |
| 3 | Surface | St-Pierre | 874 m² | Comparatif `874 m²` | ✅ |
| 4 | Zone PLU | St-Denis | Uh | Dossier/Apporteur/Gabarit/Comparatif `Uh` | ✅ |
| 5 | Zone PLU | St-Pierre | Ug | Dossier/Comparatif `Ug` | ✅ |
| 6 | Zone PLU | St-Paul | N | Dossier/Apporteur `N` · **Comparatif `—`** | ⚠️ **P5** |
| 7 | Prix ancien médian | St-Denis | 2 365 €/m² | Dossier=Bilan `2 365 €/m²` | ✅ |
| 8 | Prix ancien médian | St-Paul | 4 848 €/m² | Dossier=Bilan `4 848 €/m²` | ✅ |
| 9 | Prix ancien médian | St-Pierre | 2 946 €/m² | (fiche) | ✅ |
| 10 | Prix terrain nu zone | St-Denis | 485 €/m² | Comparatif `485 €/m²` | ✅ |
| 11 | Prix bâti section | St-Denis | 3 494 €/m² | Comparatif `3 494 €/m²` | ✅ |
| 12 | Classement LABUSE | St-Paul / St-Denis / St-Pierre | NC / D / D | Comparatif `NC·signal faible / D / D` | ✅ |
| 13 | Gabarit — zone d'implantation | St-Denis (banc) | 609 m² | Gabarit = Dossier (recette) | ✅ |
| 14 | Gabarit — hauteur | St-Denis | servie | Gabarit = Dossier (écran=PDF) | ✅ |
| 15 | SDP résiduelle | St-Denis | 26 m² (Comparatif) | ancre Z5 écran=PDF | ✅ |
| 16 | Régime TVA retenu | St-Denis | TVA sur marge (saisi) | Bilan « travaille HT » | ✅ |
| 17 | Contrainte majeure | St-Paul | Exclue (forêt domaniale) | Comparatif « Exclue : forêt domaniale » | ✅ |
| 18 | Risque bruit | St-Pierre | classement sonore | Comparatif « bruit routier » | ✅ |
| 19 | Taxe foncière (taux communal) | tous | `fiscalite.tfpb_commune_pct` | Dossier (renvoi « document Financier », cf. **P2**) | ⚠️ libellé |
| 20 | Adresse | St-Denis | 3 Chemin de la Citerne, 97417 | Dossier/Bilan en tête | ✅ |

**Mots interdits / artefacts** : scan `pdftotext` sur les 19 PDF → **0** `null/NaN/None/undefined/[object]/{{}}`, 0 code brut `tres_fort`-like, 0 zéro inventé, 0 page blanche, 0 débordement détecté. **Format FR** : dates `JJ/MM/AAAA` (0 date ISO), décimales à la virgule (0 point décimal), milliers espacés, `€/m²` / `%` espacés. **Clean.**

**Seule divergence inter-document : P5** (Zone PLU « — » au Comparatif pour St-Paul). Cause : St-Paul est une parcelle **exclue** (forêt domaniale) → la colonne `zone` servie par `/compare` (`app.py:7804`, via `_compare_row`) est `None`, alors que la fiche **dérive** `zone_famille="N"` de `reglement_plu`. Le Comparatif reflète fidèlement `/compare` (`None → «—»`) — mais la ligne est libellée *« Zone PLU · sourcé »*, ce qui fait lire « zone inconnue » quand elle est connue (N).

---

## 4. Mes documents

- **Une ligne par génération ?** Oui — `POST /documents` (documents_bibliotheque.py:65) insère **sans dédoublonnage** : deux générations du même document = **deux lignes** (P8). ⚠️ **Le Bilan s'inscrit à l'OUVERTURE de l'écran d'hypothèses** (DocumentsView.tsx:176), **avant** toute génération et **même si l'utilisateur annule** → ligne « Bilan » fantôme qui, ré-ouverte, renvoie 422 (P7).
- **Instantané des millésimes** : oui — `millesimes_servis(db)` figé en jsonb à l'insert (documents_bibliotheque.py:47,81).
- **« À jour » / « Sources modifiées depuis »** : logique juste — `a_jour` ssi tous les millésimes figés == millésimes servis aujourd'hui (documents_bibliotheque.py:133,143). **Prouvé** par `test_etat_a_jour_puis_sources_modifiees` (vert).
- **Re-télécharger = même PDF ?** Non au sens strict : **le PDF n'est jamais stocké** ; « Ouvrir » **régénère** à partir des données du jour (+ hypothèses persistées pour le Bilan). Un document « À jour » ré-ouvert après évolution des sources **changera**. Comportement assumé, mais « Ouvrir » ≠ « re-télécharger l'original ».
- **Suppression** : la route `DELETE /documents/{id}` **existe** (documents_bibliotheque.py:166) et `supprimerDocument` **existe** côté client (api.ts:1222) — **mais aucun bouton** ne l'appelle dans `LigneDoc` (boutons = Ouvrir / Excel / Régénérer seulement). **L'utilisateur ne peut pas supprimer un document** (P6).
- **Tri** : par date décroissante ; pagination « voir 200 de plus ». Chips de filtre par type + « Tous ».
- **Nom de fichier** lisible : `Dossier parcelle — DP-….pdf`, `Bilan — FI-….pdf`, `Brief apporteur — AP-….pdf`, etc. (Content-Disposition `filename*`, documents.py:83). ✅
- **Cloison** : **prouvée** (compte A voit, compte B 404 — test cloison vert ; routes dans `SCOPED_TABLES`, tenant + FK cascade).

---

## 5. Plomberie

### 5.1 Proxy Vite (dev) vs Caddy (prod) — par document

`frontend/vite.config.ts` (`apiPaths`) proxifie vers l'API les préfixes listés. **Manquent** : `/gabarit`, `/comparatif`, `/etude-zone`, `/documents`.

| Document / route | Proxy Vite (dev :5908) | Caddy (prod) | Résultat dev |
|---|---|---|---|
| `/dossier/*` | ✅ (ligne 21) | ✅ reverse_proxy catch-all (Caddyfile.prod:56) | PDF OK |
| `/financier/*` | ✅ (ligne 85) | ✅ | PDF OK |
| `/apporteur/*` | ✅ (ligne 85) | ✅ | PDF OK |
| `/pre-dossier/*` | ✅ (ligne 26) | ✅ | ZIP OK |
| **`/gabarit/*`** | ❌ **absent** | ✅ | **404 / page erreur Vite** |
| **`/comparatif.pdf`** | ❌ **absent** | ✅ | **404 / page erreur Vite** |
| **`/etude-zone.pdf`** | ❌ **absent** | ✅ | **404 / page erreur Vite** |
| **`/documents` (bibliothèque)** | ❌ **absent** | ✅ | **GET 404 → « Mes documents » toujours vide** |

→ **P1.** En prod, Caddy renvoie tout ce qui n'est pas un fichier statique du build vers `127.0.0.1:8000` (`@front` échoue sur un chemin inexistant → `reverse_proxy`), **donc les 4 routes marchent en prod**. C'est un défaut **dev-only** — mais il rend **inutilisables en `npm run dev`** la moitié des documents de la page **et** toute la bibliothèque. Preuves live : `GET /documents?limite=200 → 404` (réseau Playwright) ; onglet Gabarit = page base-URL Vite (capture `03`).

### 5.2 Gestion d'erreur côté client

- **`window.open` sans filet (P4/P3).** Dossier, Apporteur, Gabarit, Comparatif, Étude de zone s'ouvrent par `window.open(url)`. En cas de 404 (hors run), 422 (incomplet) ou 500 (technique), **le nouvel onglet affiche le JSON brut** (`{"detail":{"erreur":…}}`) — pas de message lisible, pas de retour dans la fenêtre. Seuls **le Bilan** (`FinancierQuestionnaire.ouvrirDoc` lit le 422 et liste les manques, FinancierQuestionnaire.tsx:200) et **le pré-contrôle Gabarit** (porte) gèrent proprement l'erreur.
- **Génération longue, pas de spinner (P3).** Dossier à froid = **~15 s**, Pré-dossier = **18–24 s**. L'onglet `window.open` reste **blanc** tout ce temps (seul l'indicateur natif du navigateur bouge). Aucun spinner, aucun délai max, aucun message « génération en cours ». (La tuile Dossier *de la fiche* porte un statut/quota ; la **porte** de la page Docs, non.)

### 5.3 Bibliothèque partagée entre comptes ?

**Non — cloison stricte prouvée** (§4). Un client ne voit que ses documents ; régénérer/supprimer par id d'un autre compte → 404.

---

## Tableau final des problèmes

| # | Gravité | Document | Constat | Preuve | Correctif proposé (fichier:ligne) |
|---|---|---|---|---|---|
| **P1** | **bloquant (dev)** | Gabarit / Comparatif / Étude de zone / Mes documents | Routes `/gabarit`, `/comparatif`, `/etude-zone`, `/documents` absentes du proxy Vite → en dev, PDF = page erreur Vite / 404, bibliothèque toujours vide. Prod (Caddy) OK. | captures `03`, réseau `GET /documents → 404` | ajouter `'/gabarit','/comparatif','/etude-zone','/documents'` à `apiPaths` — `frontend/vite.config.ts:19-85` |
| **P2** | **faux (client)** | Dossier | Le Dossier dit « montant chiffré dans le document **Financier** » et « Le document **Financier** les recueille… » — document nommé « Bilan » côté client. | `pdf/dossier_*.txt` l.318/441 (×3 témoins) | « Financier » → « Bilan » : `src/labuse/exports/miroir.py:1004`, `miroir.py:687`, `src/labuse/exports/blocs/bilan.py:21` |
| **P3** | gênant (UX) | tous (via porte) | Génération 15–24 s sans spinner ni délai max ; onglet blanc. | mesures §2 (Dossier 14,9 s ; Pré-dossier 23,6 s) | spinner/état dans la porte avant `window.open`, ou `fetch`+blob comme le Bilan — `DocumentsView.tsx:183-190,229-235,254-256` |
| **P4** | gênant (UX) | Dossier/Apporteur/Gabarit/Comparatif/Étude-zone | 404/422/500 → onglet montre le **JSON brut** (aucun message client). | `GET /dossier/<hors-run> → 404 {"detail":…}` | passer par `fetch`+gestion d'erreur (modèle `FinancierQuestionnaire.tsx:198-206`) — `DocumentsView.tsx:183-190` |
| **P5** | trompeur | Comparatif | « Zone PLU · sourcé » = « — » pour St-Paul (parcelle exclue) alors que fiche/Dossier/Apporteur disent « N ». | `pdf/comparatif_3.txt` l.21 ; `/compare` `zone=None` | retomber sur `reglement_plu.zone_famille` quand `zone` servie est nulle, ou libeller « — » → « N (exclue) » — `app.py:7804` (`_compare_row`) / `exports/blocs/comparatif.py` |
| **P6** | gênant | Mes documents | `DELETE /documents/{id}` et `supprimerDocument` existent mais **aucun bouton** ne supprime. | `DocumentsView.tsx:303-312` (pas de bouton) ; api.ts:1222 | ajouter un bouton « Supprimer » dans `LigneDoc` appelant `supprimerDocument` — `DocumentsView.tsx:288-315` |
| **P7** | gênant | Bilan | La ligne « Bilan » s'inscrit à l'**ouverture** de l'écran d'hypothèses, **même si on annule** → entrée fantôme qui renvoie 422 à l'ouverture. | `DocumentsView.tsx:176` | n'enregistrer qu'après génération réelle (dans `FinancierQuestionnaire` après succès) — `DocumentsView.tsx:175-181` |
| **P8** | cosmétique | tous | `POST /documents` n'a aucun dédoublonnage : relancer = nouvelle ligne. | documents_bibliotheque.py:65 | upsert par (compte, doc_type, idus, rayon) OU accepter (décision produit) — `documents_bibliotheque.py:65-83` |
| **P9** | faux (client) | page Docs | Intro « **Huit documents** » ; 7 tuiles affichées. | capture `01` ; DocumentsView.tsx:383 | « Huit » → « Sept » (ou réintroduire un 8ᵉ) — `DocumentsView.tsx:383` |
| **P10** | arbitrage | page Docs | « Courrier » (listé au mandat) **n'est pas** une tuile Docs ; c'est un outil (aperçu, sans envoi). | catalogue.ts:35-82 | décision Vic (§Questions) |
| **P11** | cosmétique | Apporteur/Dossier (fiche) | Fiche utilise une URL **littérale** non encodée (`/apporteur/${idu}.pdf`) ≠ builder encodé de la page Docs. Même route ; non-DRY. | Fiche.tsx:1961,2033 | utiliser `docApporteurUrl`/`docDossierUrl` — `Fiche.tsx:1961,2033` |
| **P12** | cosmétique | Bilan | Badge/filtre « Excel » affichés, mais `_EXCEL_DISPONIBLE` vide → jamais de bouton Excel. | documents_bibliotheque.py:44 ; catalogue.ts:44 | retirer le badge « Excel » tant que l'export n'existe pas, ou livrer l'export — `catalogue.ts:44` |

---

## Questions à trancher par Vic

1. **« Courrier » sur la page Docs ?** Le mandat le liste comme 8ᵉ document, mais dans le produit c'est un **outil** (relance propriétaire, aperçu PDF, aucun envoi côté client). Faut-il (a) ajouter une tuile « Courrier » au catalogue Docs, ou (b) corriger l'intro en « **Sept** documents » et laisser Courrier aux outils/fiche ? *(Recommandation : (b) — Courrier n'a pas la même nature « porte → PDF depuis la fiche » que les 7 autres.)*
2. **Nom « Financier » → « Bilan » (P2).** Confirmer qu'on bascule aussi les 3 prose du Dossier (`miroir.py`, `blocs/bilan.py`) sur « Bilan ». La clé interne `financier` / route `/financier` / préfixe `FI-` restent-ils inchangés ? *(Recommandation : oui — ne toucher que le texte client.)*
3. **Comparatif Zone PLU « — » pour une parcelle exclue (P5).** Doit-il afficher la zone de fond (« N ») même sur une parcelle exclue, ou garder « — » (avec un libellé qui ne dit plus « sourcé ») ?
4. **Proxy dev (P1).** Simple ajout aux `apiPaths` — mais confirmer qu'on veut un dev honnête pour les 3 nouveaux documents (DOCS-FIX-1) ; la prod n'est pas affectée.
