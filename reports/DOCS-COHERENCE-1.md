# DOCS-COHERENCE-1 — les 8 documents de Docs disent la même chose

Branche `feat/docs-coherence-1` (worktree `labuse-docs2`, ports 8830/6030). Témoins :
**97415000BY0083** (Saint-Paul, U4c, 2 458 m², 11 bâtiments, SUCCESSION CHAMCIRKAN
ARCHABY PHILIPPE) et **97408000BL0020** (La Possession, UAa). Comparatif sur
BY0083 + BY0361 + BY0272. **Pas de merge.**

## REPRISE — dernier point traité

> **Lot 0 FAIT. Lot A en cours : A1 (propriétaire), A4 (pente), A10 (date), surface
> A2/G2 FAITS et vérifiés (10 → 6 écarts harnais).** Reprendre au **Lot A reste :
> A2 (emprise au Gabarit/Apporteur/Étude), A3, A5, A6, A7, A8, A9** — entremêlés avec les lots document (D Gabarit, F Étude) ; les traiter là ou
> ici. Détail des 7 écarts restants dans le diagnostic ci-dessous.
> ⚠ 2 tests PRÉ-EXISTANTS rouges hors scope (prouvé par stash) : `test_implantation3_pdf::
> test_route_rend_un_pdf[L'Étang-Salé]` et `test_docs1_ecran_egale_pdf::test_gabarit_…` —
> parcelles de référence L'Étang-Salé absentes/dérivées de la base de TEST locale.
>
> **Complément G7 (Bilan refait maquette v3) FAIT et vérifié** — voir la section Lot G.
>
> **Suite autonome (reprise)** : FAIT A3-Gabarit (zone nommée X/Y), A7-Gabarit (hauteur
> faîtage·égout), A5 (contraintes de l'Étude = celles du Dossier §5). **Harnais BY0083 :
> 10 → 5 écarts.** Reste : zone (réconciliation moteurs gabarit/implantation/CERFA ~2,6 %),
> hauteur (CERFA pré-dossier faîtage seul), stationnement (A6), prix bâti + terrain (A8).
> Reprendre à **A6 (stationnement/pleine terre chiffrés au Gabarit)** puis A8, A9, B→F, G1-G6, H.
> Serveur API local : voir « Lancer » en bas. Harnais Bilan : `capture-bilan.html`.

---

## Lancer (rappel environnement)

```
# API (PDF-capable via le venv de labuse-main, PYTHONPATH forcé sur CE worktree) :
PYTHONPATH=$PWD/src PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj \
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  LABUSE_ENV=local DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  ~/Desktop/labuse/.venv/bin/labuse api --port 8830

# Harnais de cohérence (après fin de lot) :
PYTHONPATH=$PWD/src … ~/Desktop/labuse/.venv/bin/python -m scripts.docs_coherence 97415000BY0083
```

Gotcha : le venv `~/Desktop/labuse/.venv` est un editable qui pointe sur
`labuse-main/src`. **Sans `PYTHONPATH=$PWD/src` l'API sert le code de labuse-main, pas
ce worktree.** Le Bilan se rend EN PROCESS (sa route d'écriture exige une session
compte, absente en mode local) — même chemin que la route (`bilan.pdf.construire_pdf`).

---

## Lot 0 — harnais — FAIT

| pt | statut | preuve | note |
|----|--------|--------|------|
| 0.1 | ✅ | `scripts/docs_coherence.py` ; CSV `reports/DOCS-COHERENCE-1/before/dc-before-97415000BY0083.csv` | génère les 8 documents, extrait le texte, confronte 18 données partagées → tableau document × donnée, écart marqué `/!\`. Bilan rendu en process. |
| 0.2 | ✅ | `config/mots_interdits.yaml` v2026-10-26 (24 → 30) ; `tests/test_circuit2_lot0bis.py::test_mots_interdits_liste_versionnee` vert | +6 : « Excel », « comme dans », « dont bâti », « à confirmer — à confirmer », `&#x27;`, « parcelle(s) ». La sonde `recette_exports1` rejoue la liste la nuit (verdict distinct). |

### État « avant » (BY0083) — 10 écarts mesurés

```
donnée                 Dossier   Apporteur Prédossier ÉtudeZone Gabarit  Comparatif Faisabilité Bilan
/!\ surface terrain    2458      2458      2405       —         —        —          2458        2405
    emprise bâtie      900       —         —          —         —        —          —           —
/!\ zone impl. libérée 869       —         1699       —         869      —          1691        —
    zone impl. déduite —         —         —          —         867      —          —           —
/!\ pente              9,7°      —         —          —         —        —          14,6 %      —
/!\ hauteur faît/égout 9/6       —         9/?        —         9/?      —          9/6         —
    recul voie         4         —         —          —         4        —          4           —
/!\ stationnement      2 pl/log  —         imposés    —         non chif —          art.12.2    —
    pleine terre       40        —         —          —         —        —          40          —
/!\ prix bâti €/m²     3602      —         —          —         —        2687       —           —
/!\ prix terrain €/m²  250       —         —          —         —        479        —           —
    prix neuf VEFA     4745      —         —          —         —        —          —           —
    SDP résiduelle     —         —         —          —         —        453        —           —
    SDP max régl.      —         —         —          —         —        1327       —           —
/!\ contraintes        oui       oui       oui        —         oui      oui        AUCUNE      oui
/!\ propriétaire       pers.mor. pers.mor. particulier succession —      pers.mor.  —           —
/!\ date des données   21/10     21/10     —          21/10     21/10    21/10      27/10       —
```

**Diagnostic des 10 écarts et lot cible :**

1. **surface 2458 vs 2405** — le Dossier/Étude servent la **contenance cadastrale**
   (`parcels.contenance_m2` = 2458, doctrine « surface = contenance ») ; le **Bilan** et
   le **CERFA** servent la **surface géométrique** (`parcels.surface_m2` = 2404,9 → 2405).
   → **Lot A (surface) + G2 (terrain du Bilan)**.
2. **zone d'implantation 869 (Gabarit/Dossier §10) vs 1 691 (Étude) vs 1 699 (CERFA)** —
   aucune des deux valeurs n'est nommée (terrain libéré / bâti déduit). → **Lot A3 / D2 / F1**.
3. **pente 9,7° (Dossier) vs 14,6 % (Étude, LiDAR)** — deux sources, deux unités, jamais
   réconciliées. → **Lot A4 / F3**.
4. **hauteur** — Dossier « 9 m faîtage · 6 m égout » ; Gabarit « 9,0 m » seul ; Étude
   « 6 m » (égout) en page 1. → **Lot A7 / D2**.
5. **stationnement** — Dossier « 2 places / logement » (Sourcé) ; Gabarit « Règle connue,
   non chiffrée » ; Étude « 2 place/logt art. 12.2 » + bandeau « non modélisé ». Et sur
   résidence étudiante, 2 pl/log est **faux** (L151-35). → **Lot A6 / D2 / F6**.
6. **prix bâti 3 602 (Dossier §8) vs 2 687 (Comparatif)** ; **prix terrain 250 (Dossier,
   13 ventes « puis échantillon insuffisant ») vs 479 (Comparatif)**. Trois prix, aucun
   partagé. → **Lot A8**.
7. **contraintes** — Dossier §5 relève aléa mouvement de terrain + DPU + Parc national ;
   l'**Étude affirme « Aucune contrainte cartographiée ne touche le terrain »**. → **Lot A5 / F2**.
8. **propriétaire** — Dossier/Apporteur/Comparatif « Personne morale » ; CERFA
   « particulier » (case cochée) ; la vérité DGFiP = **SUCCESSION**. → **Lot A1 / B1 / C1**.
9. **date des données** — tous « LABUSE au 21/10/2026 » sauf l'**Étude « Généré via
   LABUSE le 27/10/2026 »** (date de génération, pas du run). → **Lot A10**.

Preuves « avant » : `reports/DOCS-COHERENCE-1/before/*.txt` (pdftotext des 8 documents),
PDF dans `reports/DOCS-COHERENCE-1/pdf/` (gitignoré).

---

## Lot A — une vérité par donnée (transverse) — EN COURS

| pt | statut | preuve / fichier | note |
|----|--------|------------------|------|
| A1 | ✅ | `proprietaire_type.libelle_proprietaire()` (classifieur unique) ; `robinet_fiche._c_proprietaire` ; `app.compare` ; `blocs/comparatif.py` | Dossier/Apporteur/Comparatif/Étude-zone : « Succession — CHAMCIRKAN ARCHABY PHILIPPE » (plus « Personne morale »). Succession/Indivision détectées (SUCCESSION/HOIRIE/HÉRITIERS/INDIVISAIRES/CONSORTS) ; tête redondante ôtée. Le CERFA « particulier » = case DEMANDEUR (pas le propriétaire) → hors comparaison. |
| A10 | ✅ | `exports/etude_faisabilite._donnees_labuse_au_etude()` | L'Étude portait « Généré via LABUSE le 27/10 » (date de génération) ; pied complété par « Données LABUSE au 21/10/2026 » (run servi, même source que les 7 autres). Harnais : date alignée partout. |
| A2 | 🟡 | `scripts/docs_coherence._bilan_pdf` (pré-remplit via `bilan.reperes.sources_parcelle`) | **surface = contenance (2458) déjà cohérente** : Dossier/Apporteur/Étude/Bilan tous 2458 ; le 2405 du Bilan était un artefact du harnais (il passait `surface_m2` géométrique au lieu du pré-remplissage produit `COALESCE(contenance_m2, surface_m2)`) — corrigé. Le « ~2405 m² surface réelle » du PCMI2 est une annotation géométrique de plan de masse (autre donnée, approximative), exclue de la comparaison. **Reste A2 vrai** : emprise bâtie n'est encore affichée que par le Dossier (900) — à servir aussi au Gabarit/Apporteur/Étude. |
| A3 | 🟡 | `robinet_fiche._gabarit` (+`zone_libere_m2`), `exports/blocs/gabarit.py`, `registre/donnees.py` (`gabarit_zone_libere_m2`) | **Gabarit FAIT** : « Zone d'implantation, terrain libéré : 1 736 m² » (X) + « …, bâti existant déduit : 869 m² » (Y) ; X − Y = 867 = emprise bâtie dans la zone. Résout la confusion « 869 vs 1 691 » du mandat (on comparait Y du Gabarit à X de l'Étude). **Reste** : Dossier §10 + Étude (label « terrain libéré ») + pré-dossier à aligner, et l'écart résiduel X : Gabarit 1 736 / Étude 1 691 / pré-dossier 1 699 = **différence de moteur** (gabarit vs implantation vs CERFA, ~2,6 %) à réconcilier (une source) — gros, hors ce commit. |
| A4 | ✅ | `pente_fmt.pente_courte()` ; `miroir.py` (couverture + §2) ; `implantation/service._pente_fiche_deg` (+`pente_fiche_pct`) ; `etude_faisabilite.py` | Source UNIQUE = fiche (RGE ALTI `parcel_terrain.pente_moy_deg`), format « 9,7° (17 %) » dans Dossier p.1+§2 et Étude §terrain (était 14,6 % LiDAR HD). Pente LiDAR du profil reste au MOTEUR (hauteur sur pente), plus affichée. Verrou `nombres_hors_payload` : 0 fuite (9,7 + 17 ancrés). |
| A7 | 🟡 | `robinet_fiche._gabarit` (hauteur string) | **Gabarit FAIT** : « Hauteur réglementaire : 9 m au faîtage · 6 m à l'égout (le gabarit extrude le faîtage) » (était « 9,0 m »). Les deux hauteurs + la base extrudée sont servies par le moteur gabarit (hauteurReglementaireM / hauteurEgoutM / hauteurBase). **Reste** : le CERFA du pré-dossier n'affiche encore que le faîtage (harnais « 9/? »). |
| A5 | ✅ | `api/modules._attach_contraintes_signalees` (via `_aleas_block` + `_dispositifs_block`), `exports/etude_faisabilite.py` §2 | L'Étude §2 porte la MÊME liste que le Dossier §5 (aléa mouvement de terrain — niveau faible, DPU…) « signalée, non interprétée (voir le Dossier §5) » ; plus jamais « Aucune contrainte » quand le Dossier en relève une. Même source (`servitudes.aleas_parcelle`). Harnais : contraintes « oui » partout. Verrou `nombres_hors_payload` : 0 fuite. |
| A6 | ⬜ | | stationnement + pleine terre chiffrés au Gabarit (« non intégrée au gabarit »). → voir D2. |
| A7 | ⬜ | | hauteur « 9 m au faîtage · 6 m à l'égout » partout ; le Gabarit dit laquelle il extrude. → voir D2. |
| A8 | ⬜ | | prix de la fiche, un seul (bâti 3602 vs 2687 ; terrain 250 vs 479). |
| A9 | ⬜ | | trois SDP, trois libellés fixes. |

**5 écarts restants (harnais BY0083)** :
1. **zone impl.** — Gabarit 1 736 (terrain libéré) / Étude 1 691 / pré-dossier 1 699 /
   Dossier §10 869 (non encore renommé) : **réconciliation de moteurs** (gabarit vs
   implantation vs CERFA, ~2,6 %) + alignement Dossier §10/Étude sur les libellés A3.
2. **hauteur** — le CERFA du pré-dossier n'affiche que le faîtage (9/?) ; Dossier/Gabarit/
   Étude = 9/6. → aligner le pré-dossier.
3. **stationnement** — Gabarit « règle connue, non chiffrée » → A6 (chiffrer 2 places /
   logement + pleine terre 40 %, « non intégrée au gabarit ») ; le harnais capte aussi
   l'« art. 12.2 » devant la valeur de l'Étude (raffiner l'extracteur ou le libellé).
4-5. **prix bâti** (3602 Dossier vs 2687 Comparatif) et **prix terrain** (250 vs 479) →
   A8 : réconcilier les 3 sources (Dossier §8 / Comparatif / Étude de zone) sur l'id fiche.

*(résolus cette session : A1 propriétaire, A2/G2 surface, A4 pente, A5 contraintes,
A7 hauteur-Gabarit, A10 date, A3-Gabarit naming, F9 format stationnement, G7 Bilan.)*

## Lot G — Bilan — G7 FAIT (complément 26/10)

**G7 — écran Bilan refait selon la maquette v3** (`docs/design/maquettes/bilan-v3.html`,
validée par Vic). Le calcul et les 45 postes NE CHANGENT PAS ; seule la présentation est
refaite. `frontend/src/components/fiche/BilanEcran.tsx`.

| élément | statut | note |
|---------|--------|------|
| En-tête collant | ✅ | « ← Docs » · Bilan / IDU / commune · ligne « Programme : Étude reliée / Choisir une Étude de faisabilité · Prix demandé : inconnu » · boutons **Exporter en PDF** / **Exporter en Excel** (grisés si CA nul — G3) + **Enregistrer** (toujours actif). |
| Ligne d'état | ✅ | « N postes pré-remplis (sourcés) · N à renseigner, comptés pour 0 · les exports s'ouvrent dès que le programme et un prix de vente sont saisis » (compté sur les lignes servies). |
| Cinq tuiles | ✅ | CA TTC · Dépenses TTC · Résultat net (vert) · Charge foncière max · Lecture (toggle « Ma marge à ce prix / Prix max du terrain »). |
| Programme en table | ✅ | Produit · Lots · SUV · Prix TTC/m² (repère + « utiliser ») · TVA · CA TTC · Total · « + Ajouter un produit ». Strip compact Terrain/SDP/Surface taxable (sourcé/repère) conservé car nécessaire au calcul (G2 : surface taxable reste vide, modifiable). |
| Calendrier compact | ✅ | à droite ; repère Sitadel « repère Sitadel · N mois » sous Obtention PC. |
| 45 postes · 4 sections | ✅ | sections repliables, **sous-total TTC dans l'en-tête de section** (« 1 · Charge foncière · 18 postes · N sourcés · TTC … »), **première ouverte** ; colonnes Libellé · Assiette · Taux ou montant · HT · TVA · TTC · État ; un seul champ, **unité à l'intérieur** ; **État en pastille** (Sourcé vert / Repère jaune / Saisi / À renseigner) à la place des liens « Sans objet ». |
| Synthèse en pied | ✅ | Dépenses TTC · CA TTC · TVA résiduelle · Résultat net · Cash-flow ; pied « Document non contractuel · Données LABUSE au 21/10/2026 ». |
| Message « Connectez-vous » | ✅ | retiré de l'écran (plus jamais affiché). |
| PDF même ordre / libellés | ✅ | `bilan/pdf.py` aligné : « n · Titre », « Total n · Titre », « Taux ou montant », pastille « À renseigner », et **G4** « N ligne(s) non renseignée(s) — comptées pour 0 » (plus « comme dans l'Excel » — 0 mot interdit au pdftotext). |

Preuves : captures `reports/DOCS-COHERENCE-1/captures/bilan-g7-{avant,apres}.png` (+ maquette
`maquette-bilan-v3.png`), rendues via le harnais `frontend/capture-bilan.{html,tsx}` (modele +
calcul par le proxy Vite, aucune auth). tsc 0 · vitest bilan OK · `vite build` OK · pytest
bilan 15 passed / 3 skipped (modèle promotrice gitignoré). ⚠ `donnees_au` ajouté au modele
(`api/bilan.py`) pour le pied daté. Adresse non servie par le modele (commune affichée) ;
pré-remplissages sourcés (G2) et en-tête complet (G6) restent à faire — hors G7.

**Reste Lot G** : G1 (choix d'une Étude), G2 (pré-remplissages sourcés), G3 (déjà appliqué
à G7), G4 (fait côté PDF + écran), G5 (alignement colonne Calendrier), G6 (en-tête complet).

## Lots B → F, G1-G6, H — à faire

(Statuts mis à jour à chaque lot ; un commit + une régénération des PDF par lot.)

- **Lot A** — une vérité par donnée (A1 propriétaire · A2 emprise · A3 zone impl. ×2 ·
  A4 pente · A5 contraintes · A6 PLU chiffré · A7 hauteur · A8 prix · A9 SDP ×3 · A10 date).
- **Lot B** — Dossier (B1..B9). **Lot C** — Apporteur (C1..C3). **Lot D** — Gabarit (D1..D2).
- **Lot E** — Étude de zone (E1..E5). **Lot F** — Étude de faisabilité (F1..F9).
- **Lot G** — Bilan (G1..G6). **Lot H** — clôture (0 écart BY0083 + BL0020, hook vert, pas de merge).
