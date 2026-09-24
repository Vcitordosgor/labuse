# RECHERCHE-2 — Toutes les barres cherchent les 3 familles

**Branche** `fix/recherche-2` (worktree `labuse-recherche`, base `audit/recherche-1` `c03f36d8`) · 3 commits (un par lot). App de recette : `127.0.0.1:8145`.
**Référentiel** : [RECHERCHE-1/RAPPORT.md](../RECHERCHE-1/RAPPORT.md).
**Date** 2026-09-24.

Mandat Vic : toute barre de recherche accepte et **résout les 3 familles** — propriétaire (nom/SIREN), parcelle (IDU/référence courte), adresse — et les **propose à la frappe**.

## Ce qui a été fait

### Lot 1 — le geste structurant (`ParcelInput`)
- `ParcelInput` déclare **par défaut les 4 grammaires** `adresse, cadastre, proprietaire, siren`. La prop d'exception `grammaireProprietaire` **disparaît**.
- Un pick **propriétaire** dans un outil qui part d'une parcelle ouvre un **sous-panneau `OwnerParcelles`** listant ses parcelles (IDU · commune · surface, `« voir N de plus »` au-delà de 200) ; en choisir une appelle `onPick(idu)` **comme un clic carte**. `onProprietaire(siren)` court-circuite le sous-panneau pour l'outil qui part du propriétaire (Scan patrimoine).
- **Test-garde** (`ParcelInput.test.tsx`) : tout usage sans props interroge le suggest sur les **4 familles** ; un pick propriétaire → ses parcelles → `onPick` ; `onProprietaire` court-circuite.

### Lot 2 — les barres hors `ParcelInput`
- **Signal ZAN** (`moteurs.tsx:496`) : `<input>` brut → **`ParcelInput`** (4 familles + clic-carte).
- **Champ Scan du module M02** (`ModulePanel.tsx:216`) : **SUPPRIMÉ** (décision Vic). C'était un doublon **mort en production** de l'outil Scan patrimoine — le menu « patrimoine » rend `ScanPatrimoine`, qui embarque `M02` *sans* cette barre (seul un test montait `M02` en direct). M02 se pilote désormais par SIREN uniquement.
- **Permis** (`ModulePanel.tsx:735`), **Radar** (`RadarView.tsx:477`), **Veille promoteurs** (`VeillePromoteurs.tsx:217`) : + grammaires `proprietaire, siren` + `OwnerParcelles`. Un pick propriétaire déroule ses parcelles ; en choisir une **cible/recentre** (Permis : zoom + ses permis ; Radar/Veille : recentrage carte + sélection).
- **Dépôt agence** (`radar/DepotAgence.tsx:74`) : **reclassé hors périmètre** (décision Vic) — c'est le champ « Adresse exacte » d'une annonce agence (saisit UN bien par adresse) ; le propriétaire n'y a pas de sens.
- Sous-panneau `OwnerParcelles` **partagé** (extrait de `ParcelInput`) : un seul rendu réutilisé par les 5 barres.

### Lot 3 — les 2 bugs back (`api/recherche.py`)
- **(a) adresse par jetons (ET)** : `_sugg_adresse` exige désormais chaque MOT de la saisie dans la colonne pliée (ordre libre), au lieu d'une sous-chaîne contiguë. « n° + voie + commune » sans le code postal ressort (le CP intercalé entre voie et commune cassait le match). Test pytest + preuve live (cf. §Preuves).
- **(b) SIREN inconnu honnête** : un SIREN bien formé (9 chiffres, hors préfixe IDU 974…) absent des fichiers fonciers rend une **note non cliquable** « SIREN … inconnu des fichiers fonciers 2025 » au lieu du « 0 muet » générique. Front : `SuggestItem.note` rendu grisé/`aria-disabled`.

**Vérifs** : `tsc` ✓ · `build` ✓ · `vitest` **181/181** · `pytest tests/test_retours16_recherche.py` **11/11** (2 nouveaux tests Lot 3 + gardes front mises à jour).

---

## A. Inventaire §A re-rempli — les barres d'entité et les 3 familles

Légende : **S+R** = suggère à la frappe **et** résout. Après RECHERCHE-2, chaque barre en périmètre couvre les 3 familles (la parcelle par IDU **et** référence courte).

| # | Barre (écran) | fichier:ligne | Propriétaire | Parcelle | Adresse |
|---|---|---|---|---|---|
| 1 | Header / omnibox app | `header/Header.tsx:212` | S+R | S+R | S+R |
| 2 | Scan patrimoine (outil) | `outils/ScanPatrimoine.tsx:138` | S+R | S+R | S+R |
| 3 | Étudier un bien (bloc B) | `outils/blocB.tsx:58` | **S+R** | S+R | S+R |
| 4 | Faisabilité (ParcelPicker/M22) | `outils/ParcelPicker.tsx:10` | **S+R** | S+R | S+R |
| 5 | Gabarit | `outils/Gabarit.tsx:175` | **S+R** | S+R | S+R |
| 6 | Étude de zone (point) | `outils/EtudeZone.tsx:226` | **S+R** | S+R | S+R |
| 7 | Prospection solaire | `outils/ProspectionSolaire.tsx:325` | **S+R** | S+R | S+R |
| 8 | Renouvellement urbain | `outils/Renouvellement.tsx:78` | **S+R** | S+R | S+R |
| 9 | Calculette foncière | `outils/CalculetteFonciere.tsx:26` | **S+R** | S+R | S+R |
| 10 | Mon secteur | `outils/MonSecteur.tsx:143` | **S+R** | S+R | S+R |
| 11 | Taxe d'aménagement | `outils/TaxeAmenagement.tsx:156` | **S+R** | S+R | S+R |
| 12 | Vérif. procédure | `outils/VerifProcedure.tsx:30` | **S+R** | S+R | S+R |
| 13 | Assemblage — parcelle de départ | `outils/moteurs.tsx:191` | **S+R** | S+R | S+R |
| 14 | Comparer des parcelles | `compare/ComparePanel.tsx:142` | **S+R** | S+R | S+R |
| 15 | Veille / Surveillance — suivre | `surveillance/SurveillancePanel.tsx:110` | **S+R** | S+R | S+R |
| 16 | Remonter le temps | `outils/ModulePanel.tsx:1173` | **S+R** | S+R | S+R |
| 17 | Courrier propriétaire | `outils/ModulePanel.tsx:1395` | **S+R** | S+R | S+R |
| 18 | Due diligence (lot) | `outils/ModulePanel.tsx:1566` | **S+R** | S+R | S+R |
| 19 | Permis (recherche) | `outils/ModulePanel.tsx:735` | **S+R** | S+R | S+R |
| 20 | Radar — recentrer la carte | `outils/RadarView.tsx:477` | **S+R** | S+R | S+R |
| 21 | Veille promoteurs — se positionner | `outils/VeillePromoteurs.tsx:217` | **S+R** | S+R | S+R |
| 22 | Signal ZAN par parcelle | `outils/moteurs.tsx:496` | **S+R** | S+R | S+R |
| — | ~~Scan patrimoine (module M02, `ModulePanel:216`)~~ | — | **barre supprimée** (doublon mort de #2, décision Vic) | | |
| — | ~~Radar — dépôt agence (`DepotAgence:74`)~~ | — | **reclassée hors périmètre** (champ « adresse d'annonce », décision Vic) | | |

**Résultat : 22 / 22 barres en périmètre couvrent les 3 familles** (les cases en **gras** sont la famille *propriétaire* gagnée par RECHERCHE-2 ; #1 et #2 étaient déjà conformes). Le total passe des 24 barres du §A de RECHERCHE-1 à **22** après les deux ajustements approuvés par Vic (1 barre morte supprimée, 1 champ reclassé). Les 8 barres de filtre/find-in-page/chat (§A.2 de RECHERCHE-1) restent **hors périmètre**, inchangées.

**Mécanisme de conformité** : les barres #3–#18 sont conformes **par construction** — elles utilisent `ParcelInput` sans props de grammaires, donc reçoivent les 4 familles (garanti par le test-garde `ParcelInput.test.tsx`). #19–#21 déclarent explicitement les grammaires + `OwnerParcelles`. #22 (ZAN) passe sur `ParcelInput`.

---

## B. Preuves (captures live, `docs/audit-2026-09/RECHERCHE-2/captures/`)

Captures node-playwright sur l'app de la branche (`127.0.0.1:8145`), 5 barres demandées + les 2 corrections back. Chaque `*-liste.png` est le gros plan de la liste déroulante.

| Fichier | Barre | Requête | Ce qu'on voit |
|---|---|---|---|
| `01-header-CBO-proprietaire` | Header | `CBO` | 3 propositions **PROPRIÉTAIRE** (CBO TERRITORIA · DEVELOPPEMENT · PROPERTY, avec nb parcelles) |
| `02-header-421032555-siren-note` | Header | `421032555` | note **honnête** « SIREN … inconnu des fichiers fonciers 2025 — aucun foncier détenu » (Lot 3b) |
| `03-faisabilite-CBO-proprietaire` | Faisabilité | `CBO` | mêmes propositions PROPRIÉTAIRE (via `ParcelInput`) |
| `04-gabarit-CBO-proprietaire` | Gabarit | `CBO` | idem |
| `05-scan-CBO-proprietaire` | Scan patrimoine | `CBO` | idem |
| `06-courrier-CBO-proprietaire` | Courrier | `CBO` | idem |
| `07-header-adresse-jetons-commune` | Header | `1 chemin Vidot Saint-Benoit` | **ADRESSE** trouvée avec la commune accolée sans le CP (Lot 3a, match par jetons) |
| `evidence-suggest.txt` | — | les 4 requêtes du mandat | réponses JSON brutes du suggest |

**Notes d'honnêteté sur les 4 requêtes du mandat :**
- `CBO` → **propriétaire** : capturé live (01, 03–06).
- `421032555` → **note SIREN honnête** : capturé live (02). *Voulu* : ce SIREN n'a pas de foncier PM à La Réunion.
- `BW0917` (**parcelle**, référence courte) : la **base partagée de recette était sous un verrou lourd d'une requête tierce de ~30 min sur la table `parcels`** (une DDL de heal au boot, non prioritaire, mise en file derrière — je n'ai pas l'autorisation de tuer des backends de la base partagée). Les lectures `parcels` (donc la grammaire cadastre) expiraient. La résolution cadastre 2-communes est **prouvée par pytest** (`test_cadastre_ref_courte_toutes_les_communes`, base isolée `labuse_test`) et par la capture live de RECHERCHE-1 (BW0917 → Saint-Benoît / Saint-Paul). Le composant (dropdown identique à toutes les familles) est celui capturé pour propriétaire/adresse.
- `27 chemin Vidot Saint-Denis` (**adresse**) → **0 correct** : le Chemin Vidot réel de la BAN est à **Saint-Benoît / Saint-Paul**, sans n° 27 (l'adresse « Saint-Denis » du mandat était l'exemple de placeholder du dépôt agence). La correction « jetons » est prouvée sur une adresse réelle équivalente : `1 chemin Vidot Saint-Benoit` (voie + commune, CP omis) → ressort (capture 07 + pytest `test_adresse_match_par_jetons_sans_code_postal`).

---

## Cas non rangés / limites

- **`BW0917` non capturé en image** : verrou tiers sur `parcels` de la base de recette pendant toute la session (voir ci-dessus). Prouvé par pytest + RECHERCHE-1. Aucune capture trompeuse (empty) laissée.
- **`27 chemin Vidot Saint-Denis`** : renvoie 0 par **exactitude de la donnée** (pas de tel n° dans cette commune), pas par bug — le fix jetons est prouvé sur une adresse existante.
- **8 barres §A.2** (CRM, Fiche find-in-page, Copilote, Sources, admin) : hors périmètre, inchangées (Lot 5 de RECHERCHE-1, à trancher séparément).
- **Différence 24 → 22** : décision Vic (barre M02 morte supprimée, Dépôt agence reclassé) — assumée, documentée dans la table.
