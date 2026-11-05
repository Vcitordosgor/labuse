# NU5-B — Chaque document, page par page

**Mandat.** Relire chaque document que l'app produit (PDF, Excel, CSV), page par page, sur
10 parcelles variées : chiffres comparés à l'écran au même instant (un écart d'un euro ou
d'un m² compte), dates et millésimes en fuseau de La Réunion, mentions obligatoires, mise
en page, cohérence interne, « Régénérer », badge « Sources modifiées depuis », cas difficiles.

**Cadre.** Branche `audit/nu5-b`, worktree `~/Desktop/labuse-nu5b`, API locale `:9740`
(auth désactivée en local), serveur PDF capable `labuse/.venv` (weasyprint 70), base **locale
`labuse`** (434 582 parcelles, run q_v20). **LECTURE SEULE** : aucune écriture, aucune
correction, prod jamais touchée ni sondée. Généré le **05/11/2026** (heure de La Réunion).

**À lire d'abord.** Digéré avant de commencer : la lignée EXPORTS (`docs/audit-2026-09/EXPORTS/`),
`EXPORTS-REBRANCHEMENT-1/2`, `DOCS-AUDIT-1`, et surtout **NU-3 Lot I**
(`docs/audit-2026-11/nu-3/I/RAPPORT.md`) — dont le harnais (hits endpoint + `pdftotext`/`pdfinfo`/
`pdffonts`/`pdftoppm`, ~20 témoins) sert de modèle ici.

---

## 1. Verdict

Le socle documentaire est **solide** : sur ~70 PDF générés, **0 mot interdit**
(`None/null/NaN/undefined/{{…}}`), **0 police de secours** (toutes embarquées), **0 page blanche**,
**régénération déterministe** (texte identique hors horodatage sur *tous* les PDF), **chiffres =
écran au m²/€ près** (contenance, SDP restante, zones PLU — y compris parcelles à cheval —
concordent sur les 10 parcelles), **dates correctes en fuseau Réunion**, mise en page nette
(accents, tableaux sans débordement, badges `sourcé`/`estimé`, numéros de page), et **refus
honnêtes** (422 motivés, jamais 500, jamais un PDF à moitié rempli).

**Une faille de fond ressort, à cause unique :**

> **Une parcelle disparue du cadastre est refusée par le Dossier, le Gabarit et le Comparatif,
> mais l'Apporteur, l'Étude de zone et surtout *Estimer un bien* composent quand même un document
> complet — carte avec contour, zone PLU, et un prix estimé à 2 917 €/m² — sur une parcelle qui
> n'existe plus.** Même parcelle, même instant : « aucune donnée servie » d'un côté, « 2 917 €/m² »
> de l'autre.

Classe du défaut = **garde `cadastre_disparue` posée sur certaines routes, oubliée sur trois
autres** (même forme que les manques de garde vus en NU4-A).

---

## 2. Étape 0 — Catalogue des documents produits

| # | Document (nom client) | Type | Point d'entrée (route) | Renderer (fichier:ligne) | Moteur |
|---|---|---|---|---|---|
| 1 | **Dossier** (de parcelle) | PDF | `GET /dossier/{idu}.pdf` | `api/dossier.py:69` → `exports/builder.construire` | WeasyPrint |
| 2 | **Flash** (79 €) | PDF | achat Stripe → `GET /flash/telecharger` | `flash/report.py:130` (Jinja `rapport.html.j2`) | WeasyPrint. *= Dossier* (cf. REBRANCHEMENT) |
| 3 | **Bilan** (dossier financier) | PDF | `GET /financier/{idu}.pdf` | `api/documents.py:97` | WeasyPrint |
| 3b | Bilan — **Excel** | XLSX | `GET /bilan/{idu}.xlsx?doc_id=…` | `api/bilan.py:415` → `bilan/excel.py` | openpyxl (formules vivantes) |
| 4 | **Apporteur** (brief) | PDF | `GET /apporteur/{idu}.pdf` | `api/documents.py:102` (`forms=True`) | WeasyPrint |
| 5 | **Pré-dossier PC** | ZIP (6 PDF + LISEZMOI) | `GET /pre-dossier/{idu}.zip` | `api/pre_dossier.py:1068` | PyPDF2 (CERFA) + FPDF2 (plans) + WeasyPrint |
| 6 | **Gabarit** (enveloppe) | PDF | `GET /gabarit/{idu}.pdf` | `api/documents.py:129` → `builder.construire_gabarit` | WeasyPrint |
| 7 | **Comparatif** | PDF (A4 paysage) | `GET /comparatif.pdf?idus=X,Y[,Z]` | `api/documents.py:158` | WeasyPrint |
| 8 | **Étude de zone** | PDF | `GET /etude-zone.pdf?idu=…&rayon_km=…` | `api/documents.py:190` | WeasyPrint |
| 9 | **Étude de faisabilité** (Assemblage) | PDF | `POST /modules/etude/pdf` | `api/modules.py:2418` (sous-processus isolé) | WeasyPrint |
| 10 | **Estimer un bien** (analyse d'annonce) | PDF | `GET /analyse-annonce/{idu}.pdf` · `…?url=` | `api/documents.py:249` / `:282` | WeasyPrint |
| — | **Courrier** | PDF | `api/courrier.py` | — | WeasyPrint |
| — | **Export signalements** | CSV | `GET /signalements/export.csv` | `api/app.py:9154` | csv (séparateur `;`, BOM) |

Redirections (308) : `/dossier-banquier/{idu}.pdf` et `/argumentaire/{idu}.pdf` → `/financier/{idu}.pdf`.
Infrastructure partagée : `exports/rendu.py:218 render_pdf` (pool de sous-processus, RLIMIT, recyclage —
NU4-FIX-1), CSS unique `exports/theme.css`, polices OFL embarquées (`api/fonts/`), cartouche pied
`@bottom-left` « Données LABUSE au … ».
**Facture** : il n'existe **aucun PDF de facture interne** — les factures sont **hébergées par Stripe** ;
la mention fiscale vit dans `config.facture_mention` (source unique, identique au pied Stripe).

---

## 3. Les 10 parcelles témoins

| # | IDU | Commune | Catégorie visée | Caractéristique vérifiée |
|---|-----|---------|-----------------|--------------------------|
| 1 | `97415000BO0852` | Saint-Paul | **bâtie** | bati_max, U1a, PPR bleue, 2 bâtiments 540 m², propriétaire moral MCA3 |
| 2 | `97415000CW0658` | Saint-Paul | **nue + à cheval** | nu, 3 zones AU3a/AU3h/N, SDP 38 619 m² |
| 3 | `97421000AB0133` | Salazie | **zone rouge partielle + à cheval** | PPR rouge 15 % + bleue, zones N/Aba/A, sans adresse |
| 4 | `97411000DN0183` | Saint-Denis | **copropriété** | copro RNIC + DVF, à cheval Ui/N |
| 5 | `97424000AM0893` | Cilaos | **AU + propriétaire très long** | AUb, SEM « AMENAGEMENT DE DEVELOPPEMENT ET D EQUIPEMENT DE LA REUNION » |
| 6 | `97417000BN0002` | Saint-Philippe | **sans zone PLU / très grande** | forêt domaniale, 515 500 m², sans adresse |
| 7 | `97416000DV0285` | Saint-Pierre | **surface incertaine** | contenance 1 m² vs plan 117 505 m², PPR, propriétaire Commune |
| 8 | `97418000AV2114` | Sainte-Marie | **sans données** | **disparue du cadastre** (2026-09-01), remplacée par 3 parcelles |
| 9 | `97411000BZ1065` | Saint-Denis | bâti témoin | Uh, chemin de la Citerne (parcelle de contrôle) |
| 10 | `97409000AK0804` | Saint-André | **nue constructible + PPR** | UB, SDP 35 086 m², PPR rouge+bleue |

Cas difficiles couverts : parcelle sans données (#8), **disparue** (#8), propriétaire très long (#5),
adresse absente (#3, #6), surface discordante (#7), 30 parcelles dans un Comparatif (§5-F4).

---

## 4. Ce qui tient (crédits, prouvés)

1. **0 fuite / 0 mot interdit** sur ~70 PDF : aucun `None/null/NaN/undefined`, aucun `{{var}}`,
   aucune clé interne (`EPSG`, `ST_*`, `q_v20`, `SOFT_FLAG`, `work_mem`, `Traceback`). Seule occurrence
   relevée : le mot « doctrine » dans le LISEZMOI du pré-dossier, en français courant (« Doctrine :
   LABUSE ne sert jamais un CERFA dont le millésime n'est pas confirmé ») — non fautif (cf. §5-O1).
2. **Polices toutes embarquées** (`pdffonts` : 0 police non-embarquée sur tous les PDF) → aucune police
   de secours à l'affichage/impression.
3. **0 page blanche** (texte 228–1 400 caractères/page même sur les études longues).
4. **Régénération déterministe** : 2ᵉ passe sur chaque PDF → texte **identique** après neutralisation
   de l'horodatage. Les chiffres ne bougent pas ; seuls le n° de rapport (`DP-20261105-xxxx`) et le
   « généré le » changent, comme attendu.
5. **Chiffres = écran (±0)** : contenance, SDP restante, et **toutes** les zones PLU concordent entre
   le PDF et la fiche API (= l'écran) sur les 10 parcelles. Parcelles à cheval : les 3 zones
   d'`CW0658` (AU3a/AU3h/N) servies à l'identique ; bâti `BO0852` 540 m² / 73 % cohérent.
6. **Dates en fuseau Réunion** : « généré le **05/11/2026** » + n° `DP-20261105-…` sur chaque dossier ;
   « Données LABUSE au 21/10/2026 » = millésime data, cohérent partout. Apporteur : « Émis le 05/11/2026 —
   valable 90 jours (jusqu'au **03/02/2027**) » — calcul +90 j exact.
7. **Mise en page nette** : accents (é/è/à/°/²/—) parfaits, tableaux sans débordement, badges
   `sourcé`/`estimé` lisibles, numéros de page (« 3 / 10 »), sauts de page propres, cartes ortho nettes.
8. **Refus honnêtes et motivés** : `financier` et `gabarit` renvoient **422 `document_non_etablissable`**
   avec la liste des manques (jamais 500, jamais un PDF à moitié rempli). Honnêteté structurelle.
9. **Parcelle sans données (Dossier)** : message clair, 1 page — « Parcelle disparue du cadastre
   (version du 2026-09-01). Remplacée par : …. Aucune donnée n'est servie ; les documents ne peuvent
   pas être composés. »
10. **Nom de propriétaire très long** (SEM, `AM0893`) : s'enroule proprement, aucun débordement.
11. **TVA franchise 293 B** présente **là où la facture apparaît** — page `/flash` : « TVA non
    applicable, art. 293 B du CGI », lue de `config.facture_mention` (source unique = pied de facture
    Stripe). Les PDF d'analyse ne sont pas des factures → absence de mention TVA correcte.
12. **Badge « Sources modifiées depuis »** fonctionnel : la bibliothèque `/documents` distingue bien
    `a_jour` (47) de `modifie` (99) en comparant l'instantané des millésimes à l'instant présent
    (`api/documents_bibliotheque.py:137`).

---

## 5. Trouvailles classées

### 🔴 MAJEUR — F1 · Parcelle disparue : trois documents composent une analyse sur une parcelle qui n'existe plus

**Preuve.** Parcelle `97418000AV2114` (Sainte-Marie), **disparue du cadastre le 2026-09-01**,
remplacée par `AV2932/AV2930/AV2931`. Au même instant, mêmes requêtes :

| Document | Comportement | Correct ? |
|---|---|---|
| **Dossier** | Refuse : « Parcelle disparue… Aucune donnée n'est servie ; les documents ne peuvent pas être composés. » | ✅ |
| **Comparatif** | 422 « parcelle_disparue » | ✅ |
| **Gabarit** | 422 « parcelle_disparue » | ✅ |
| **Apporteur** | Compose un brief complet de 3 pages : « Un terrain à sonder — terrain a priori nu », carte, champs de contact | ❌ |
| **Estimer un bien** | Compose 2 pages : carte ortho **avec contour vert de la parcelle**, zone « **UB** », « aucune vente depuis 2014 », puis **PRIX ESTIMÉ AU M² = 2 917 €/m²** (de 2 485 à 3 834 €/m²), « Fiabilité Moyenne, 57 ventes », tableau des **8 ventes comparables** | ❌ |
| **Étude de zone** | Compose 9 pages centrées sur la parcelle | ❌ (moins grave : le rayon existe) |

Aucun de ces trois documents ne mentionne la disparition. *Estimer* invente même une **zone PLU (UB)**
que la fiche ne sert pas (fiche `AV2114` : zones `[]`, état `None`). Captures :
`captures/AV2114_analyse_p1-1.png`, `captures/AV2114_apporteur_p1-1.png`.

**Cause racine (lue dans le code).** La garde `cadastre_disparue.info_disparue` (CHASSE-DONNEES-FIX-1,
Lot 2) est posée sur `dossier` (`api/dossier.py:101`), `gabarit` et `comparatif`
(`api/documents.py:137,170`) et `courrier` — **mais absente** de :
`apporteur_pdf` (`documents.py:102`), `etude_zone_pdf` (`:190`), `analyse_annonce_parcelle_pdf`
(`:249`) et `analyse_annonce_lien_pdf` (`:282`). Vérifié route par route :

```
apporteur_pdf                guard_disparue=False
gabarit_pdf                  guard_disparue=True
comparatif_pdf               guard_disparue=True
etude_zone_pdf               guard_disparue=False
analyse_annonce_parcelle_pdf guard_disparue=False
analyse_annonce_lien_pdf     guard_disparue=False
financier_pdf                guard_disparue=False  (protégé incidemment : 422 « programme » requis)
```

**Correction suggérée (non appliquée — audit lecture seule) :** étendre l'appel `info_disparue`/
`phrase_disparue` déjà existant à `apporteur`, `etude-zone`, `analyse-annonce` (parcelle **et** lien),
comme pour le Gabarit.

---

### 🟠 MOYEN — F2 · L'avertissement juridique manque sur 3 documents client

L'avertissement « Document d'information… Ne remplace ni un certificat d'urbanisme, ni une étude de
faisabilité réglementaire, ni un conseil juridique » figure en pied du **Dossier**, du **Bilan** et du
**Gabarit**. Il est **absent** de l'**Étude de zone** et du **Comparatif** (aucune mention du type
« ne remplace pas / caractère indicatif / conseil juridique »). L'**Apporteur** ne porte que son
avertissement de confidentialité (« Ne vaut pas mandat ») ; **Estimer** porte un avertissement de
valorisation (« ce n'est pas un avis de valeur ») mais pas l'avertissement réglementaire.
→ Un document remis à un tiers (Comparatif, Étude de zone) devrait porter le même garde-fou que le
Dossier. Mention voulue par le mandat : « ni conseil juridique ni garantie de constructibilité ».

### 🟠 MOYEN — F3 · Le Comparatif plafonne silencieusement à 3 parcelles

`GET /comparatif.pdf?idus=<30 IDU>` → PDF de 2 pages titré « **3 parcelles** · CO-20261105-0004 ·
05/11/2026 ». Les **27 autres parcelles sont abandonnées sans aucun avertissement**. Le sous-titre
dit « Deux à trois parcelles côte à côte » mais rien n'indique à l'utilisateur que sa demande a été
tronquée. (Le front limite probablement la sélection, mais l'endpoint, lui, tronque en silence —
cf. doctrine « no silent caps : log what was dropped ».) Capture :
`preuves/_difficiles/comparatif_30.pdf`.

### 🟡 MINEUR — F4 · « garantie de constructibilité » n'est écrit nulle part

La formule exacte « ni garantie de constructibilité » attendue par le mandat n'apparaît dans **aucun**
document. Le Dossier la couvre *implicitement* (« ne remplace pas une étude de faisabilité
réglementaire »), mais l'assurance explicite — importante vu que LABUSE sert des verdicts de
constructibilité — manque.

### 🟡 MINEUR — F5 · Étude de zone non bornée en commune dense

`etude-zone` de `DV0285` (Saint-Pierre) = **36 pages** : les pages 10 à 36 **énumèrent nommément tous
les établissements** du rayon 1 km (ECLIPSE · Autres services ; BOUTIQUE LINDA 974 · Commerces ;
CABINET DU DR PATRICE GUIRA · Santé ; HÔTEL CAP SUD · Tourisme ; …). Aucune borne (top-N) ni résumé.
Une parcelle rurale rend 2-3 pages. Un document client de 36 pages listant chaque commerce est peu
exploitable (déjà signalé « 9-24 pages » en NU-3 Lot I). Ergonomie.

### 🟡 MINEUR — F6 · Surface incertaine : en-tête non qualifié

`DV0285` : l'en-tête affiche **« 1 m² »** en gros (contenance cadastre) alors que le plan dessine
**117 505 m²** — discordance que la fiche signale (`surface_incertaine=True`,
« le plan et le cadastre ne concordent pas »). Le Dossier **porte** l'avertissement, mais **enfoui**
en p. ~13 (« Analyse incomplète — surface incertaine : le plan et le cadastre ne concordent pas »),
pas à côté du chiffre de tête. Un lecteur qui survole lit « 1 m² » comme un fait.

### 🟡 MINEUR — F7 · PDF sans métadonnée CreationDate

`pdfinfo` ne montre **aucune** `CreationDate` dans les métadonnées (weasyprint ne l'estampille pas).
La date de génération est bien dans le corps (fuseau Réunion) ; seules les **métadonnées** sont vides —
sans conséquence visible, mais un archivage/outil tiers qui lit les métadonnées ne trouvera pas de date.

### 🟡 MINEUR — F8 · Badge « modifié » comparé à TOUTES les sources servies

`documents_bibliotheque.py:137` compare l'instantané du document à l'intégralité des millésimes servis
*aujourd'hui*, pas au **sous-ensemble** de sources réellement utilisé par ce document. Un document peut
donc passer « Sources modifiées depuis » parce qu'une source **sans rapport** a changé de millésime
(99/146 sont « modifié »). Sur-signalement possible. (Comportement documenté, mais perfectible.)

### ⚪ Observation — O1 · pré-dossier LISEZMOI : notation `{IDU}-labuse-<pièce>.pdf`

Le LISEZMOI du ZIP écrit : « Toutes les pièces suivent la doctrine `{IDU}-labuse` :
« 97415000BO0852-labuse-<pièce>.pdf » ». `{IDU}` et `<pièce>` sont une **méta-notation** décrivant le
schéma de nommage (un exemple concret suit), pas des variables non substituées. Non fautif, mais à
reformuler pour lever l'ambiguïté (un lecteur peut croire à un gabarit non rempli).

---

## 6. Fiches par document

Pour chaque document : pages lues, écarts, captures. Détail machine dans `preuves/resultats.json`
(1 entrée par parcelle × document : http, pages, polices, mots interdits, mentions, régénération).

### Dossier (`/dossier/{idu}.pdf`) — 1 à 11 pages
- **Pages lues** : 10×1-11 p (BO0852 10 p, DV0285 11 p, AV2114 1 p refus).
- **Écarts** : aucun sur les chiffres (contenance/SDP/zones = écran). F6 (surface incertaine, en-tête).
- **Solide** : avertissement juridique présent ; généré-le + n° rapport en fuseau Réunion ; badges
  `sourcé`/`estimé` ; régénération déterministe. Capture `captures/BO0852_dossier_p3-03.png`.

### Bilan — PDF (`/financier/{idu}.pdf`) + Excel (`/bilan/{idu}.xlsx`)
- **PDF** : 422 `document_non_etablissable` pour 9/10 parcelles (programme constructible manquant) —
  refus honnête ; 200/5 p sur `BZ1065`. Avertissement juridique présent.
- **Excel** : exige `?doc_id=` (document de bibliothèque). Non généré faute de doc Bilan stocké en base
  locale (bibliothèque = 146 docs *étude-faisabilité*). Moteur openpyxl à formules vivantes (hérité,
  non ré-audité ici). *Dette : rejouer l'Excel après génération d'un Bilan.*

### Apporteur (`/apporteur/{idu}.pdf`) — 3 à 4 pages
- **Écart** : **F1** (compose sur parcelle disparue). Avertissement **confidentiel** présent, mais pas
  l'avertissement juridique (F2). `forms=True` : champs remplissables OK.

### Pré-dossier PC (`/pre-dossier/{idu}.zip`) — 6 PDF + LISEZMOI
- **Membres** : CERFA (13406 pour `BO0852`), PCMI1/2/4/7-8, règles-zonage, LISEZMOI.
- **Dates** : tous les fichiers du ZIP datés **2026-11-05** (plus le bug « 1980/CET » de NU-3 Lot I).
- **Écart** : O1 (notation de nommage). Sinon conforme, millésime CERFA confirmé.

### Gabarit (`/gabarit/{idu}.pdf`) — 3 pages
- 422 honnête quand non calculable (7/10) ; 200/3 p sinon. Garde `cadastre_disparue` **présente**.
  Avertissement juridique présent.

### Comparatif (`/comparatif.pdf`) — 2 pages (A4 paysage)
- **Écarts** : **F3** (plafond 3 silencieux) ; **F2** (pas d'avertissement juridique). Garde
  `cadastre_disparue` présente (422 sur parcelle disparue). Chiffres alignés sur l'écran.

### Étude de zone (`/etude-zone.pdf`) — 2 à 36 pages
- **Écarts** : **F1** (compose sur parcelle disparue) ; **F2** (pas d'avertissement juridique) ;
  **F5** (36 pages non bornées en zone dense). Carte + rayon nets.

### Estimer un bien (`/analyse-annonce/{idu}.pdf`) — 2 pages
- **Écart majeur** : **F1** (prix estimé 2 917 €/m² + carte + zone sur parcelle disparue). Variante
  « par lien » : 422 honnête quand l'annonce n'a pas été relevée (« url_bloquee »). Avertissement de
  valorisation présent. Capture `captures/AV2114_analyse_p1-1.png`.

### Étude de faisabilité / Assemblage (`POST /modules/etude/pdf`)
- Exige une config (parcelles + programme) ; rendu en **sous-processus isolé** (NU4-FIX-1). Refus
  propre « au moins une parcelle est requise » sur payload vide. Bibliothèque `/documents` : 146
  entrées étude-faisabilité, badge `a_jour`/`modifie` correct. *Assemblage 30 parcelles : moteur lourd,
  non stress-testé ici (couvert par etude-v6-1) ; le plafond à surveiller est côté Comparatif (F3).*

### Export CSV signalements (`/signalements/export.csv`)
- 200, séparateur `;`, BOM UTF-8, dates **ISO en +04:00** (heure Réunion). Conforme.

---

## 7. Harnais (reproductible)

`harnais/harnais.py` — **lecture seule**. Pour chaque parcelle :
1. **Génère** chaque document (`GET`), enregistre l'octet brut dans `preuves/<idu>/`.
2. **Extrait** : `pdfinfo` (pages, date), `pdffonts` (police de secours ?), `pdftotext -layout`
   (texte), `pdftotext -f/-l` (texte page par page → pages blanches), décompresse le ZIP pré-dossier.
3. **Snapshot écran** : `GET /parcels/{idu}` (fiche JSON = ce que l'écran rend) → `fiche.json`.
4. **Contrôle** : mots interdits / fuites, placeholders `{VAR}`, mentions (avertissement, sources,
   TVA 293 B, coordonnées), dates `généré le` / `Données LABUSE au`, **régénération** (2ᵉ passe,
   diff hors horodatage).
5. Sortie agrégée `preuves/resultats.json`.

Scripts d'appoint (dans ce rapport, non versionnés en fichier) : comparaison chiffre-à-chiffre
PDF↔fiche, classification des parcelles, test Comparatif 30, rendu PNG (`pdftoppm`) des pages clés.

**Rejouer :**
```bash
# API déjà lancée sur :9740 (venv PDF-capable)
PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj PYTHONPATH=$PWD/src \
  ~/Desktop/labuse/.venv/bin/python -m labuse.cli api --port 9740 &
cd docs/audit-2026-11/nu-5/B/harnais
~/Desktop/labuse/.venv/bin/python harnais.py          # 10 parcelles × 8 documents
```

**Pièges de poste** (confirmés) : pas de `.venv` dans le worktree → utiliser
`~/Desktop/labuse/.venv/bin/python` + `PYTHONPATH=…/labuse-nu5b/src` ; `weasyprint` **ne s'importe
pas** sous l'env conda `labusedb` (pango absent) → serveur PDF via le `.venv` seulement ;
`LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse` (rôle OS `openclaw`,
pas `labuse`).

---

## 8. Récapitulatif des trouvailles

| ID | Gravité | Document(s) | Trouvaille |
|----|---------|-------------|------------|
| **F1** | 🔴 MAJEUR | Apporteur, Estimer, Étude-zone | Composent une analyse (prix, zone, carte) sur une parcelle **disparue du cadastre** — garde `cadastre_disparue` oubliée sur 3 routes |
| **F2** | 🟠 MOYEN | Étude-zone, Comparatif (Apporteur, Estimer partiel) | Avertissement juridique absent |
| **F3** | 🟠 MOYEN | Comparatif | Plafonne **silencieusement à 3 parcelles** (30 demandées → 27 abandonnées sans avis) |
| **F4** | 🟡 MINEUR | tous | « garantie de constructibilité » écrit nulle part |
| **F5** | 🟡 MINEUR | Étude de zone | 36 pages non bornées en commune dense (liste nominale de tous les établissements) |
| **F6** | 🟡 MINEUR | Dossier | Surface incertaine : en-tête « 1 m² » non qualifié, caveat enfoui |
| **F7** | 🟡 MINEUR | tous les PDF | Pas de métadonnée `CreationDate` |
| **F8** | 🟡 MINEUR | Bibliothèque | Badge « modifié » comparé à *toutes* les sources, pas au sous-ensemble du document |
| **O1** | ⚪ Obs. | Pré-dossier LISEZMOI | Notation `{IDU}-labuse-<pièce>.pdf` à reformuler |

**Dette** : (a) rejouer le **Bilan Excel** après génération d'un Bilan (doc_id) ; (b) **Flash** acheté
(flux Stripe) non testé — réputé = Dossier (REBRANCHEMENT) ; (c) **Assemblage 30 parcelles**
(étude-faisabilité, moteur lourd) non stress-testé ; (d) rejouer les routes gardées **en pilot/prod**
(auth désactivée en local).

---

*Audit NU5-B — lecture seule, base locale, prod jamais touchée. Harnais et preuves dans
`docs/audit-2026-11/nu-5/B/`. Commit sur `audit/nu5-b`.*
