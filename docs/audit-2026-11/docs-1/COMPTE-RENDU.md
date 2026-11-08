# DOCS-1 — compte-rendu

> Branche `fix/docs-1`, worktree `~/Desktop/labuse-docs1`, Opus. Base Mac `labuse` (run servi
> `q_v20`, 434 582 parcelles), rendu PDF in-process (venv `~/Desktop/labuse/.venv`, weasyprint 70,
> `LABUSE_PDF_PROCESS_ISOLE=0`). **Aucun merge, aucun accès prod.** Pièce à conviction lue d'abord :
> `~/Desktop/LABUSE-EXPORTS-2026-11-07/` (16 documents sur `97411000BZ1065` + `SOMMAIRE.md`),
> `docs/audit-2026-11/nu-5/B/RAPPORT.md`, `docs/audit-2026-11/ecarts-zero-1/COMPTE-RENDU.md`.

## Décision de Vic appliquée

« Un fait a une seule valeur dans tous les documents, celle de la fiche. Chaque correction se fait
à la source, jamais document par document. Plus aucun mot de cuisine interne dans un document
client. Un seul format partout. » Documents **Argumentaire**, **Dossier banquier**, **Lettre de
zonage** et **Financier** (builder-exports) **supprimés** ; le **Courrier** garde l'unique point
d'entrée ; le **Bilan** (écran Bilan, `/bilan/{idu}.pdf`) est le seul document financier.

---

## 0. Le résultat — le banc des documents

NOUVEAU `scripts/coherence/documents_banc.py` + test `tests/test_docs1_banc.py` (reel+local) :
rejoue **tous les documents servis** sur les **12 parcelles témoins** et REFUSE tout fait imprimé à
deux valeurs, tout jeton de cuisine interne, toute faute de format.

| Contrôle | Avant | Après |
|---|---:|---:|
| Faits à deux valeurs | 7 | **0** |
| Jetons de cuisine interne | 44 | **0** |
| Fautes de format | 14 | **0** |
| **Total** | **65** | **0** |

```
PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj PYTHONPATH=$PWD/src \
  ~/Desktop/labuse/.venv/bin/python -m scripts.coherence.documents_banc    # → VERT, 0 écart
```

---

## 1. Suppression des quatre documents (à la source)

**Argumentaire, Dossier banquier, Lettre de zonage** (commit 1) — routes de redirection
(`api/documents.py`), robinets registre (`pdf_argumentaire`/`pdf_banquier`/`pdf_lettre_zonage`),
rate-limit (`protection.py`), porte Copilote (`_DOC_MAP`), front (vite, strings, capaciteMax, api,
useApp, copilote, constructibilite), tests, QA. Table RGPD `lettre_zonage_refs` **conservée** (purge
des données personnelles historiques).

**Financier** (builder-exports, commit 2) — **il n'était plus accessible depuis l'app** (aucun
composant `FinancierQuestionnaire` ; rien n'ouvre `/financier/{idu}.pdf` ; la carte Bilan ouvre
`<BilanEcran>` → `/bilan/{idu}.pdf`). Supprimé entièrement : route + 3 routes questionnaire ;
modules `exports/blocs/financier.py`, `exports/financier_bilan.py`, `financier_questionnaire.py` ;
dispatch/contexte builder. **« Les postes restent dans le Bilan »** : robinets `pdf_financier` →
`pdf_bilan` (`/bilan/{idu}.pdf`) et `ecran_questionnaire_financier` → `ecran_bilan`, chiffres
conservés (aucun orphelin, graphe du registre valide). Tests financier supprimés/trimés.

**Effet de bord voulu** : la divergence `sdp_max_terrain` (Financier « 325 m² » inventé vs fiche
« 212 m² ») disparaît avec le document.

---

## 2. Les deux faits moteur unifiés

| Fait | Valeur unique (fiche) | Correctif |
|---|---|---|
| **Servitude PPR** | 1 servitude — PM1 | Le **Gabarit** lisait les SUP de la seule géométrie modélisée (« Aucune SUP ») : il LIT désormais `dispositifs.sup` de la fiche (`_dispositifs_block`, même lecteur que le Dossier) et retire la règle moteur contradictoire. |
| **SDP maximale, terrain** | la valeur de la fiche | Le Financier (qui composait un programme de logements non saisi → « 325 m² ») est supprimé (§1). |

---

## 3. Jetons, format, abréviations, forme

**Jetons de cuisine interne** — `config/mots_interdits.yaml` 30 → **48** (version `2026-11-07`,
test `test_circuit2_lot0bis` maj), corrigés **au producteur** :
`capacite_max.MENTION` (py+ts : « volet D », « VERITE-TERRAIN »), `etude_faisabilite` (« verrou de
test », « géométrie servie »), `gabarit/builder.py` (« config/ », « troncon_de_route »),
`exports/blocs/gabarit._clean_src` via `risques_arbitrage.libelle_client_detail`
(« INONDATION_MOUVEMENT_DE_TERRAIN », « PM1_PPR_… », « édition non enregistrée »),
`millesime_source.libelle_date_source` (« ingéré le » → « au »), `exports/blocs/annonce` (« Classement
D », « 0 · Non retenue » → on garde le motif factuel), déclarations fiche (« parcelle hors run servi »
→ « non évalué(es) pour cette parcelle »). **Banc : 0 jeton.**

**Format** — date ISO → jj/mm/aaaa (`millesime_source.composer` + filet `miroir._mill_client` pour le
cache de fiche), décimale point → virgule (`exports/blocs/zonage._regles`). **Banc : 0 faute.**

**Abréviations du Bilan** — **SUV** écrit en clair (« surface vendable ») dans le PDF, l'Excel et le
moteur (`bilan/moteur.py`, `pdf.py`, `excel.py`). DROC/DAT/TRE/GIEP/M.O.D./Pack vivaient dans le
Financier builder-exports, supprimé — plus présentes. **Excel** : taux (TVA, marge) affichés « 8,5 % »
(format `0.0 %`), jamais « 0.085 ».

**Forme** — Dossier : « Vérifié : rien » → « Vérifié : rien à signaler » ; le **§11 « Simulation »**
(renvoi au Financier supprimé) DISPARAÎT de la structure unique (sommaire + corps), « Limites et
sources » remonte §12 → §11. Apporteur : case « Vides » → « Vide ». **Courrier** : en-tête, signature
et pied au **nom du client** (marque blanche, repli sur le nom du compte), JAMAIS « LABUSE » ni « pour
le compte de LABUSE » (`api/courrier._pdf_header`/`_marque_du_compte`, `courrier_compose`). Captures
avant/après : `docs/audit-2026-11/docs-1/captures/` (le Courrier « avant » portait l'en-tête + pied
« LABUSE » ; « après » porte l'identité du compte).

---

## 4. Prix — un seul prix en titre, les autres en annexe « Marché »

Le prix EN TITRE est celui du **type de bien de la parcelle** (maison pour une maison), avec sa
définition en une ligne (type · ventes · rayon · période). Le mécanisme `type_prioritaire` de
`sector_price` existait mais ne tirait le type que de la dernière vente DVF de la parcelle : un bâti
qui n'a jamais muté (ex. `97411000BZ1065`) retombait sur « appartement » en tête d'un dossier de
maison. **DOCS-1** (`marche_service.marche_dvf`, point d'appel UNIQUE) : à défaut de vente DVF, un
**bâti non en copropriété est une maison** → fiche, Dossier, Comparatif, Estimer deviennent
type-exacts ENSEMBLE (lecteur unique). Les autres indicateurs (terrain nu, médianes par type, neuf
VEFA) restent en **annexe Marché** du §8, chacun défini. Exemple : `BZ1065` passe de « 2 365 €/m² —
appartement » à « **3 821 €/m² — maison (29 ventes à moins de 500 m, 2022–2025)** ».

## 5. Forme (point 7) — tous les items

- **Couvertures (carte + résumé)** : Dossier (carte de situation remontée en page de garde, résumé =
  bandeau de tuiles), Comparatif (carte + résumé d'une ligne), Bilan (carte + CA TTC / Résultat net).
- **Pied de page raccourci** : l'Étude ne répète plus IDU/type/« généré le » ; le numéro de page tient
  sur une ligne (`@bottom-right` nowrap).
- **Page quasi vide du Flash** : supprimée (c'était le §11 « Simulation », retiré).
- **3D du Gabarit** : enveloppe **limitée au plafond d'emprise** (homothétie) + mention « le bâti
  existant dépasse la hauteur autorisée (X m mesurés / Y m autorisés) ».
- **Tuile manquante de l'Étude de zone** : rangée de tuiles de tête ajoutée.
- **Carte d'Estimer** : fond ortho IGN + contour + voisines (déjà servis ; vérifié).
- **« Valeur du terrain » d'Estimer** : expliquée en une phrase quand elle dépasse la valeur du bâti.
- **PPR une seule fois dans l'Étude de faisabilité** : la zone rouge/bleue a sa ligne dédiée, plus
  re-listée parmi les contraintes signalées.
- **Corps du Courrier au nom du client** : l'intro, les ouvertures et l'offre sont au nom de
  l'expéditeur ; **0 « LABUSE » dans le recto** — LABUSE n'apparaît qu'en mention discrète d'outil au pied.

## 6. Recette

| Recette | Résultat |
|---|---|
| **Banc des documents** (12 témoins, 43 documents) | **0 écart** (faits 0, jetons 0, format 0) |
| **Régénération V2** (`~/Desktop/LABUSE-EXPORTS-2026-11-07-V2/` + `SOMMAIRE.md`) | `scripts/docs1_regen_v2.py` — 3 parcelles : `97411000BZ1065`, `97409000AK0804` (**nue zone U**), `97421000AB0133` (**zone rouge partielle**). TOUS les documents survivants rendus, **Bilan PDF + Excel compris** (saisies illustratives, comme l'export d'origine ; la GÉNÉRATION du Bilan lit `declarations/bilan/postes.yaml`, pas le modèle Excel — celui-ci ne sert qu'aux tests golden `test_bilan_*`). |
| Captures couvertures avant/après | `docs/audit-2026-11/docs-1/captures/` |
| Hook (unitaires `not db/local/reel/network`) | **vert** (le flake `test_courrier_transitions_journalisees` est pré-existant, ignoré) |

---

## 7. 2ᵉ passe — « la V2 contenait encore ces défauts, que le banc ne voyait pas »

Le banc V2 ne rendait que `dossier/gabarit/apporteur/estimer` : il ne VOYAIT ni le Comparatif, ni
l'Étude, ni le **Flash**, ni le Courrier, ni le Bilan. **Élargi** (`documents_banc.py`) à TOUS les
documents (POST compris) et à deux faits de plus — **viabilisation** et **date du PPR** — sur
**13 parcelles témoins** (dont une **zone U touchée par la zone rouge d'un PPR**, `97415000CY0275`, et
la zone N `97421000AB0133`). Il a révélé **163 écarts**, tous corrigés **à la source** → **0 écart**.

| Fait / jeton / forme | Avant | Correctif (à la source) |
|---|---|---|
| **Viabilisation** à deux valeurs | dossier « probable » vs comparatif/Flash « confirmée » | `viabilisation.build_indicateur` — **un seul libellé** (« probable ») lu par fiche, Dossier, Comparatif, Flash, Estimer. |
| **Date du PPR** à deux valeurs | dossier « approuvé le 16/04/2026 » (édition DEAL de TOUTE l'île) vs Estimer « 2012 » | `deal_carmen` + `millesime_source` — le millésime de couche DEAL ne se lit plus « approuvé le … » ; seule la date du PPR **de la commune** s'affiche. |
| **Flash = Dossier** | le Flash exporté était une copie du Dossier | le **vrai produit 79 €** (`generate_flash_report`) ; jargon retiré (« run servi », « sentinelle », « ingéré le », « Version du modèle »), dates jj/mm/aaaa, décimales à la virgule. |
| **Étude** : plafond d'emprise 487 vs 470 | 30 % du DESSIN | le plafond **du Gabarit** (CES × contenance), lu dans le payload. |
| **Étude** : 4 bâtiments vs 2 | `count(DISTINCT b.id)` (doublons d'ingestion) | `bati.stats_batch`/`emprise_bati_bdtopo_m2` — **mêmes producteurs que la fiche** (dédoublonnés). |
| **Étude** : « art. Article Uh.9 », millésime ISO | — | `_art_label` (« art. Uh.9 »), `_fr_iso` (jj/mm/aaaa), décimales à la virgule à la sortie. |
| **Courrier / Apporteur** : nom = e-mail | le nom de compte (souvent l'e-mail) servait de signataire | société, sinon prénom + nom ; **jamais l'e-mail** ; sans nom → le document **refuse** (« Renseignez le nom de votre société dans Compte »). Signature sous « Cordialement, ». |
| **Bilan** : bénéfice sans coût | résultat = CA (dépenses nulles) | sans coût majeur saisi → **« non calculable — saisissez vos coûts »** ; ligne « Terrain » = **contenance** de la fiche. |
| **Forme** | « Pack », « )) » | sous-groupe Bilan renommé ; parenthèses imbriquées supprimées (quartier, relief). |

Le **Gabarit** sur une parcelle **zone N** rend désormais un **document de refus propre** (jamais un
422) ; sur la **zone U + PPR rouge**, il se dessine EN déduisant le rouge.

## 8. Recette (2ᵉ passe)

| Recette | Résultat |
|---|---|
| **Banc des documents élargi** (13 témoins, 123 documents, Flash/Courrier/Bilan/Étude compris) | **0 écart** (faits 0, jetons 0, format 0) |
| **Régénération V3** (`~/Desktop/LABUSE-EXPORTS-2026-11-07-V3/` + `SOMMAIRE.md`) | `scripts/docs1_regen_v3.py` — 4 parcelles ; **Flash réel**, Gabarit de refus (zone N), Bilan « non calculable ». 44 documents (l'Étude de `CY0275` refuse honnêtement : le moteur d'implantation ne produit pas de scénario sur cette géométrie). |
| Hook (unitaires `not db/local/reel/network`) | **vert — 2953 passed** |

---

*DOCS-1 — base locale, prod jamais touchée. Banc : `scripts/coherence/documents_banc.py` ;
régénération : `scripts/docs1_regen_v2.py` (V2) et `scripts/docs1_regen_v3.py` (V3). Branche
`fix/docs-1`, non mergée.*
