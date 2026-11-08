# DOCS-DA-1 — compte-rendu

> Branche `feat/docs-da-1`, worktree `~/Desktop/labuse-docs-da`, Opus. Base locale `labuse` (run servi
> `q_v20`), rendu PDF in-process (venv `~/Desktop/labuse/.venv`, weasyprint 70,
> `LABUSE_PDF_PROCESS_ISOLE=0`). **Aucun merge, aucun accès prod.** Référence visuelle validée par Vic :
> `docs/design/maquettes/gabarit-documents-A.pdf` (les polices du PDF de maquette sont de remplacement ;
> la règle est **Inter + JetBrains Mono**). Lectures d'abord : la maquette, `INVENTAIRE.md`
> (inventaire-dossier-1), `docs/audit-2026-11/docs-1/COMPTE-RENDU.md`.

## Étape 0 — préalable

`fix/docs-1` **est** mergé dans `origin/main` (`c959d351e Merge branch 'fix/docs-1'`, et la branche
figure dans `git branch --merged origin/main`). Préalable rempli — le mandat s'exécute.

---

## A — Le gabarit (à la source, une fois pour tous)

Réécriture de `src/labuse/exports/theme.css` + câblage des polices (`exports/rendu.py`).

- **Papier blanc partout.** Le SEUL aplat sombre est le **bandeau de couverture** (`.cover-banner`,
  bleed jusqu'aux bords via marges négatives). Aucune page entière sombre.
- **Deux familles, polices EMBARQUÉES.** Inter aux **quatre poids réels 400/500/600/700**, instanciés
  depuis la fonte variable `Inter-Regular.ttf` (`fontTools`) → `Inter-Regular/Medium/SemiBold/Bold.ttf`.
  **Plus de Space Grotesk** (il usurpait le gras et faussait la famille) ni de repli **Verdana**. La mono
  des références cadastrales reste JetBrains Mono (famille CSS « IBM Plex Mono »).
- **Une échelle unique, six tailles, rien sous 10,5 px** : `--fs-xxl 34` (adresse de garde) · `--fs-xl 20`
  (titres de section, valeurs des tuiles) · `--fs-lg 13,5` (verdict, référence mono, sous-titre) ·
  `--fs-md 12,5` (texte, valeurs) · `--fs-sm 11` (libellés, groupes, sommaire, badges) · `--fs-xs 10,5`
  (en-tête courant, pied, légendes, sources). **Mesuré au rendu : plancher 7,88 pt = 10,5 px exactement**
  sur tous les documents.
- **Couverture (Dossier)** refaite d'après la maquette (`miroir.cover_dossier`) : bandeau LABUSE + nom du
  document, référence en mono, **adresse en 34 px**, sous-titre (lieu · type de bien · zone), plan de
  situation, **six tuiles-chiffres**, sommaire paginé, cartouche du bas (n° de rapport · généré le ·
  **données à jour au** = date du run servi), disclaimer sur **une ligne sans date**. **Pas de légende des
  badges** en couverture.
- **Pages** : en-tête courant d'une ligne (LABUSE · document · référence · adresse), titre de section
  numéroté à barre verte, encadré de verdict vert/ambre/gris, lignes « libellé / valeur / badge » à trois
  colonnes, encadrés « Vérifié : rien à signaler » / « Non disponible ici », figures en cadre 1 px avec
  légende, pied d'une ligne avec pagination. Paysage pour le seul Comparatif.

## B — Le Dossier (rangé)

- **Ordre des sections** appliqué à la DÉCLARATION (`declarations/fiche/sections.yaml`), source unique de
  l'ordre : **1 Identité · 2 Urbanisme · 3 Potentiel · 4 Risques et environnement · 5 Terrain · 6 Bâti ·
  7 Réseaux et desserte · 8 Marché · 9 Fiscalité et dispositifs · 10 Quartier · 11 Limites et sources**.
  Le Dossier PDF (miroir de cette liste) et le résumé Copilote (`sections_fiche()`) suivent. *Réserve :*
  l'écran compose ses tiroirs par un ordre JSX codé en dur (`Fiche.tsx`, FICHE-RANGEMENT-2), que ce lot
  **n'a pas** réordonné (front laissé inchangé, comme DOCS-1) — rendre l'écran miroir du nouvel ordre est
  une suite FRONT identifiée.
- **Sources rassemblées au §11** : le pied « Sources : … » SOUS chaque section est retiré
  (`miroir.rendu_sections`) ; les noms de sources vivent au seul §11.
- **Retraits** (côté Dossier ; l'écran garde ses lignes — ensembles `_RETIRES_DOSSIER` /
  `_RETIRES_ABSENCE_DOSSIER` dans `miroir.py`) : identifiants RNB, adresses BAN PLUS, APER
  (`enr_exclue_parcelle`), GéoMCE (`mesures_compensatoires_parcelle`), « hors rayon TCSP »
  (`tcsp_stationnement_allege`), **part de sol nu à 0 %**, **piscine quand absente**, **historique de
  détention** nul (`proprietaire_timeline_liste`), **VEFA** quand l'échantillon est insuffisant (absence
  non imprimée), **FRR** (`_dispositifs_block` — non applicable fiscalement à La Réunion). Les « RETIRER »
  de l'inventaire marqués « Absent ✓ » (HLM, bâti avant 1990, RPLS commune, Filosofi large) étaient déjà
  hors Dossier : « ne pas ajouter » respecté.
- **Correction DÉFAUT — productible solaire.** Le Dossier imprimait « Productible solaire : non calculé »
  À TORT : la fiche détient la valeur dans `viabilisation.solaire.prod_kwh_kwc` (le MÊME faisceau que
  l'écran, qui en tire « Ensoleillement très favorable »). `robinet_fiche._c_solaire` lit désormais cette
  source → « **1 548 kWh/kWc** ». Le fait entre au **banc des documents** (`_productible`).

### B — faits ajoutés : état

Le défaut explicitement signalé (productible solaire « non calculé » faux) est **corrigé** et au banc. Les
autres faits de la liste d'ajout de l'inventaire (pente maximale + alerte terrassement, hauteur à l'égout
mesurée, acquéreurs pro < 300 m/36 mois, permis de section/36 mois, fourchette DVF Q1–Q3, 8 comparables,
loyer OLL, Filosofi 200 m, gestionnaires de réseaux nommés, bus au contact, taux départemental de TA,
saturation de densité, niveaux max, vue 3D à côté du 2D, CatNat si complet) **restent à câbler** : chacun
exige son extracteur (`robinet_fiche`), son rendeur (`miroir`) et son entrée au banc. **Non livrés dans ce
lot** — identifiés comme suite B (le gabarit, l'ordre, les retraits et la correction solaire étant le socle
prioritaire validé visuellement).

## C — Les dix autres documents

- **Moteur WeasyPrint** (Bilan, Apporteur, Gabarit, Comparatif, Étude de zone, Étude de faisabilité,
  Estimer, Courrier) : héritent de `theme.css` ; les tailles bespoke sous 10,5 px (CSS d'Apporteur /
  Estimer dans `builder.py`, `etude_faisabilite.py`) passent à `var(--fs-xs)`. Les **légendes SVG du
  Gabarit** (`gabarit/plan_svg.py`) reçoivent `font-family="Inter"` (fin du repli Verdana) et des tailles
  agrandies (≥ 10,5 px rendus). Les attributions « Généré via LABUSE » (`api/documents.py`,
  `api/dossier.py`) passent à 10,5 px.
- **Flash** (moteur propre, `flash/templates/rapport.css`) : Space Grotesk → Inter (4 poids), tailles
  < 10,5 px relevées (dont `blocs_documents.py`).
- **Pré-dossier PC** (fpdf2, `pre_dossier.py` / `pdf_premium.py`) : police d'affichage Space Grotesk →
  **Inter-Bold** ; tailles des pages WeasyPrint annexes relevées. *Réserve :* la petite typographie des
  cellules du formulaire CERFA (fpdf2) n'a PAS été bousculée (mise en page réglementaire sensible) — à
  traiter séparément.
- **Courrier** : forme de lettre conservée, mêmes polices, même pied.

---

## Recette

| Recette | Résultat |
|---|---|
| **Banc des documents** (`scripts/coherence/documents_banc.py`), **13 témoins canoniques, 130 documents** | **VERT — 0 écart** (faits à deux valeurs 0, jetons de cuisine interne 0, fautes de format 0, incohérence capacité/PPR 0). |
| **Banc des documents**, 4 parcelles de la régénération (BZ1065, AK0804, DH0076, AB0133) | **VERT — 0 écart**. Un faux positif pré-existant « Excel » ⊂ « Excel­lente » (classement A d'une parcelle au Comparatif) corrigé à la source : un jeton alphabétique ne matche plus s'il est suivi d'une lettre. |
| **Test gabarit** `tests/test_docs_da_1.py` (`reel`+`local`, PyMuPDF) | **3 passed** — aucun fond sombre pleine page, polices embarquées (Inter/JetBrains/DejaVu uniquement), aucune taille sous 10,5 px (plancher mesuré 7,88 pt = 10,5 px). |
| **Régénération V8** `scripts/docs1_regen_v8.py` → `~/Desktop/LABUSE-EXPORTS-2026-11-07-V8/` + `SOMMAIRE.md` | 4 parcelles, **45 documents** (Flash/Bilan+Excel/Apporteur/Pré-dossier/Gabarit/Comparatif/Étude de zone/Étude de faisabilité/Estimer/Courrier). |
| **Captures avant/après** | `docs/audit-2026-11/docs-da-1/captures/` (avant = V7, après = V8), un PNG par document + la page 2 du Dossier. |
| **Hook** (unitaires `not db/local/reel/network`) | **vert — 3182 passed, 50 skipped** (2 tests mis à jour au nouvel ordre / à la légende HTML du gabarit : `test_exports2_lot2`, `test_plan_svg`). |

### Polices (contrôle `pdffonts` / PyMuPDF)

Chaque PDF embarque Inter (400/600/700), IBM-Plex-Mono (JetBrains) et, au besoin, DejaVu en repli
système — **plus aucune Space Grotesk ni Verdana**.

---

## Ce qui reste (honnêtement)

1. **Faits ajoutés B** (14 faits au-delà du solaire) — à câbler (extracteur + rendeur + banc).
2. **Miroir écran** du nouvel ordre de sections (réordonner le JSX de `Fiche.tsx`) — suite FRONT.
3. **Pré-dossier PC** — typographie du formulaire CERFA (fpdf2) à aligner sans casser la mise en page légale.
4. Reculs des limites séparatives → phrase courte, et masquage des codes bruts résiduels (NAF/US5) —
   polissages de l'inventaire non bloquants.

---

*DOCS-DA-1 — base locale, prod jamais touchée. Banc : `scripts/coherence/documents_banc.py` ;
test gabarit : `tests/test_docs_da_1.py` ; régénération : `scripts/docs1_regen_v8.py`. Branche
`feat/docs-da-1`, non mergée.*
