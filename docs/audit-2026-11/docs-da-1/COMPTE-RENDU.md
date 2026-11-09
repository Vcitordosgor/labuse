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

## V10 — six écarts avec la maquette corrigés (relecture Vic)

1. **Pied de page sur une ligne, SANS date, tous documents** — la date de la donnée ne vit qu'en
   COUVERTURE (« Données à jour au »). Retirée des pieds des exports (`builder._FOOT`), de l'Étude de
   faisabilité, du Bilan (`bilan/pdf.py`). Testé : `test_pied_de_page_sans_date` (bande basse de chaque
   page, aucune date). L'attribution « Sources : DVF · Radar LABUSE » de l'Estimer est conservée (sans date).
2. **Polices : « IBM Plex Mono » → « JetBrains Mono » partout** (nom réellement embarqué) ; le **Courrier**
   passe sous le gabarit — **Inter embarquée** (fpdf2 `add_font`, plus d'Helvetica de base), forme de
   lettre conservée, même pied. Testé sur les **11 documents** : `test_polices_embarquees_inter_jetbrains_sur_11_documents`
   (aucune IBM Plex Mono / Space Grotesk / Verdana ; Helvetica des champs de formulaire tolérée).
3. **§Potentiel — 2D et 3D dans deux cadres de MÊME taille côte à côte**, légende sous chacun
   (`.gabarit-plan svg { height: 46mm; border }`, viewBox letterboxé → même rectangle).
4. **PPR — une seule date** : l'**approbation du PPR de la COMMUNE** (`aleas[].ppr[].approbation`), jamais
   la date d'édition de la couche DEAL (île entière). Le millésime d'édition DEAL est omis de la ligne
   d'aléa (`miroir._r_aleas`). Le fait banc **`date_ppr` attrape la régression** : il capture désormais
   aussi « dernière édition DEAL du … AAAA » → un document qui porte deux dates PPR = écart (prouvé : le
   banc a flashé ROUGE sur DH0076/AB0133 avant le correctif, VERT après).
5. **Productible solaire : « 1 548 kWh/kWc — très favorable »** — le qualificatif vient de la MÊME lecture
   que la fiche (`viabilisation.solaire.qualite`), via `_c_solaire` (dict) + rendeur `_r_solaire`.
6. **Plus aucune ligne « Sources : » sous une section** dans le **Flash** (template), le **Gabarit**
   (`pied(valeurs, IDS)` retiré) et l'**Étude de zone** (note reformulée sur la seule mise en garde
   d'échelle). La section dédiée « Mentions / Sources » (= §11 Limites et sources) reste.

**Recette V10** : banc des documents **VERT — 0 écart** (4 parcelles ET 13 témoins/130 docs) ; test gabarit
`tests/test_docs_da_1.py` **4 passed** (fond, polices 11 docs, tailles, **pied sans date**) ; hook vert ;
régénération **V10** (`scripts/docs1_regen_v10.py`).

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

### B — les 15 faits ajoutés (V9) — LIVRÉS

Chaque fait est lu au **même robinet que la fiche** (extracteur `robinet_fiche` sur le payload `/parcels`,
ou moteur PARTAGÉ avec Estimer/le Gabarit), déclaré au registre (`donnees.py` + robinet + oracle), rendu
par un rendeur (`miroir`) et **vérifié par le banc des documents**. Le front de la fiche n'est pas touché
(les déclarations pilotent le Dossier/miroir, pas le JSX de l'écran).

| Fait | Source (même lecteur) | Section |
|---|---|---|
| Pente maximale + alerte terrassement | `terrain.pente_max_deg` / `flag_terrassement_lourd` (RGE ALTI) | 5 Terrain |
| Hauteur à l'égout **mesurée** | `le_bien.hauteur_egout_m` (LiDAR HD) | 6 Bâti |
| Acquéreurs pro < 300 m/36 mois, nommés et datés | `pm_voisines.acquereurs` (DVF × DGFiP PM) | 1 Identité |
| Permis de la **section** cadastrale/36 mois | `depots.secteur` (Sitadel) | 8 Marché |
| Fourchette DVF (Q1–Q3, min/max) | `prix_ancien` (DVF) | 8 Marché |
| Les **8 comparables** les plus proches, **comme Estimer** | `rapport_parcelle().estimation.comparables` (même lecteur qu'Estimer) | 8 Marché |
| Loyer de marché **OLL** | `loyers_oll` | 8 Marché |
| Niveau de vie **Filosofi 200 m** | `marche_secteur.filosofi_200m` | 10 Quartier |
| **Gestionnaires** de réseaux nommés | `gestionnaires` (eau/assainissement/élec/SPANC) | 7 Réseaux |
| Ligne de **bus au contact** | `proximites.transport_ligne` (OSM/GTFS) | 7 Réseaux |
| **Taux départemental** de taxe d'aménagement | `taxe_amenagement.taux_departemental_pct` | 9 Fiscalité |
| **Saturation** de la densité (consommé/résiduel) | `potentiel_transformation.pct_consomme/pct_residuel` | 3 Potentiel |
| **Niveaux maximum** | `potentiel_transformation.calcul.niveaux_max` | 3 Potentiel |
| **Vue 3D** du gabarit **à côté** du schéma 2D | `gabarit_svg_3d` (moteur Gabarit) — deux colonnes | 3 Potentiel |
| Arrêtés **CatNat** (si le compte est complet) | `catnat` + garde `CATNAT_REFERENCE` (06/09, troncature réparée) | 4 Risques |

**Tendance DVF : un seul lecteur** — `prix_ancien.tendance` (le même que le Flash et le secteur) ; rien si
non servi. **Ne PAS ajouter** (respecté) : établissement SIRENE à l'adresse, marge à l'égout, valeur du
terrain nu, score de vente. **Banc** : 11 faits numériques/comparables entrent au banc
(`pente_maximale`, `hauteur_egout_mesuree`, `acquereurs_pro_n`, `permis_section_n`, `comparables_sig`,
`loyer_oll`, `filosofi_nivvie`, `taux_dep_ta`, `niveaux_max_da`, `catnat_total`, `tendance_dvf`) + le
productible solaire. Faux positif pré-existant « Excel » ⊂ « Excellente » corrigé à la source.

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
| **Régénération V9** `scripts/docs1_regen_v9.py` → `~/Desktop/LABUSE-EXPORTS-2026-11-07-V9/` + `SOMMAIRE.md` | 4 parcelles, tous les documents, **avec les 15 faits ajoutés**. (La V8 — gabarit seul — reste `scripts/docs1_regen_v8.py`.) |
| **Captures avant/après** | `docs/audit-2026-11/docs-da-1/captures/` (avant = V7, après = V9), un PNG par document + la page 2 du Dossier. |
| **Hook** (unitaires `not db/local/reel/network`) | **vert** (contrôles d'intégrité du registre satisfaits : 17 ids ajoutés à `donnees.py` + robinet `/parcels` + oracle ; 4 ids « moteur »→`passe_plat`, 1 phrase d'absence reformulée au vocabulaire). |

### Polices (contrôle `pdffonts` / PyMuPDF)

Chaque PDF embarque Inter (400/600/700), IBM-Plex-Mono (JetBrains) et, au besoin, DejaVu en repli
système — **plus aucune Space Grotesk ni Verdana**.

---

## Ce qui reste (honnêtement)

1. **Miroir écran** du nouvel ordre de sections (réordonner le JSX de `Fiche.tsx`) — suite FRONT (un autre mandat s'en charge ; le front n'est pas touché ici).
2. **Pré-dossier PC** — typographie du formulaire CERFA (fpdf2) conservée (mise en page réglementaire).
3. Reculs des limites séparatives → phrase courte, et masquage des codes bruts résiduels (NAF/US5) —
   polissages de l'inventaire non bloquants.

---

*DOCS-DA-1 — base locale, prod jamais touchée. Banc : `scripts/coherence/documents_banc.py` ;
test gabarit : `tests/test_docs_da_1.py` ; régénération : `scripts/docs1_regen_v8.py` (gabarit),
`scripts/docs1_regen_v9.py` (gabarit + 15 faits). Branche `feat/docs-da-1`, non mergée.*
