# AUDIT M95 — trois communes 100 % ANC : vérification de la source

**Mandat M95 · Phase 1 (vérifier la source, STOP obligatoire) · branche `feat/m95-anc-trois-communes` · NON mergé**

Doctrine : *Sourcé / Estimé / Absent* · *la source réglementaire prime* · *fraîcheur = date
de la source amont* · *aucune valeur sur parole* · *un critère = un seul endroit*.

On ne grave pas un Sourcé sur une citation de seconde main. Ce document vérifie l'affirmation
« Salazie, La Plaine-des-Palmistes, Petite-Île = 100 % ANC » avant tout branchement.

## 1. Confirmation de l'affirmation (source primaire + concordantes)

- **Source primaire — Office de l'eau Réunion, Chronique de l'eau.** Le repo porte déjà un
  seed VERSIONNÉ transcrit du texte p.13 : `data/anc/office_eau_chronique_149_2023.csv`. Il
  affirme explicitement :
  - `97421 Salazie → 100 % ANC (commune 100 % ANC, texte p.13)`
  - `97406 La Plaine-des-Palmistes → 100 % ANC (texte p.13)`
  - `97405 Petite-Île → 100 % ANC (texte p.13)`
  (le seed liste aussi Saint-Philippe 95 %, Le Port 8 %, Saint-Denis 15 %, île 46 %.)
- **Vérification INDÉPENDANTE (web).** Le document original du mandat existe
  (Chroniques n°111, 17/03/2020, eaureunion.fr). Une recherche confirme que **les trois
  communes sont entièrement en ANC** et que le SPANC est géré par la **CIREST** (Salazie,
  La Plaine — compétence reprise le 01/01/2020) et la **CIVIS/CISE** (Petite-Île) — les
  secondes sources concordantes (RPQS) que le mandat mentionnait.
- **Concordance INSEE (M88).** Taux de NON-raccordement au collectif, RP2022 (maille commune) :
  Salazie **97,81 %**, Petite-Île **96,65 %**, La Plaine **94,74 %** (IRIS 92-100 %). Cohérent
  avec « commune intégralement ANC » — le résidu 2-5 % est du bruit d'enquête (gardiennage,
  quelques foyers déclarés raccordés), pas un secteur collectif. `anc.calage_office_eau` croise
  déjà ces deux chiffres.

*(Note : mes premières mesures ont utilisé de MAUVAIS codes INSEE — La Plaine est 97406 (pas
97409), Petite-Île 97405 (pas 97417). Corrigé : les trois confirment ~95-98 %.)*

## 2. Le millésime réel

- Le mandat cite la Chronique **n°111 (2020)**. Le repo porte une source PLUS RÉCENTE et
  concordante : **Chronique n°149 (publiée déc. 2025, données 2023)** — déjà seed versionné.
- **Recommandation millésime : n°149, données 2023** (la source la plus récente qui l'affirme),
  pas 2020. Cela répond aussi à la question du mandat « aucun zonage plus récent n'a créé un
  secteur collectif depuis ? » : le document 2023 **reconfirme** le 100 % ANC — rien n'a changé
  entre 2020 et 2023. La date servie = la date de la source amont (2023), jamais l'ingestion.

## 3. Cohérence avec l'existant

- **Aucune parcelle de ces 3 communes n'a de `zone_anc` (M86-B)** — 0 sur 26 622 parcelles
  (Salazie 7 035, Petite-Île 13 137, La Plaine 6 450). **Aucun conflit** à prévoir.
- **Statut ANC actuellement servi** : M88 SECTEUR (« Dans ce secteur, ~95 % des logements ne
  sont pas raccordés », taux IRIS/commune). Le mandat propose de le REMPLACER par un Sourcé
  d'ÉCHELLE COMMUNE (« commune classée intégralement en ANC ») — plus fort et réglementaire.

## 4. État de la source dans `data_sources`

« Office de l'eau Réunion — Chroniques de l'eau » existe (status `connecte`, documentation_url
= PDF n°149), `source_millesime` VIDE aujourd'hui. Usage actuel : calage/contrôle croisé
uniquement (masquée à l'affichage /sources, arbitrage M86/M87). Pour servir un Sourcé, il
faudra RENSEIGNER son `source_millesime` (n°149, données 2023) — la fraîcheur voyagera de là.

## STOP — Vic valide la source et le millésime

- **Affirmation confirmée** par une source primaire (Office de l'eau) + deux concordantes (INSEE
  RP2022, gestion SPANC CIREST/CIVIS). Robuste, pas une citation de seconde main.
- **Millésime proposé** : Chronique n°149 / données 2023 (recommandé), au lieu du n°111/2020 cité
  par le mandat — c'est la source la plus récente qui reconfirme, et elle écarte l'objection
  « un collectif créé depuis 2020 ».
- **Aucun conflit** M86-B ; concordance M88 (94-98 %).

Question pour Vic : valide-t-on le millésime **n°149 / 2023** (recommandé) ou tient-on au
**n°111 / 2020** du mandat ? Rien n'est branché avant cette validation (interdit du mandat).
Si Vic refuse la source, ces communes restent en l'état (statut M88 secteur).

---

## Phase 2+3 — branchement (arbitrages rendus)

STOP validé : **millésime n°149 / données 2023** ; **commune Sourcé EN TÊTE + secteur INSEE en corroboration**.

**Branché — via le point unique `anc_service`, aucune branche parallèle :**
1. **Ingestion** (`ingestion/anc.py::load_office_eau_communes`) : matérialise `anc_office_eau_commune`
   (insee, commune, pct_anc, millésime, source_ref) depuis le SEED versionné (jamais en dur), et
   renseigne `data_sources.source_millesime` de l'Office de l'eau (fraîcheur = date amont). Câblé au
   CLI (`ingest-anc`, étape proba/tout). 6 communes chargées, 3 intégrales (pct ≥ 100).
2. **`anc_service.statut_anc`** : nouvelle branche `source_commune` APRÈS le parcellaire (M86-B), AVANT
   le secteur (M88). Lit `anc_office_eau_commune` (garde `to_regclass` : table absente → retombe sur
   secteur, jamais un crash). Sert : « {commune} est classée INTÉGRALEMENT en ANC (commune entière —
   pas un secteur ni un zonage à la parcelle) — {source} ({millésime}). Corroboré : INSEE {taux} %… ».
   **Les 3 échelles de Sourcé sont distinctes** : `source` (parcelle) / `source_secteur` (secteur) /
   `source_commune` (commune) — la phrase dit toujours laquelle.
3. **Rendu 4 documents + fiche** : `blocs_documents.anc_bloc` (label « Sourcé commune », ligne
   « Échelle : commune entière · millésime », CSS mint), `pdf_premium` (état vert), front
   (`AncStatut.statut` + `ANC_BADGE.source_commune` « Sourcé · commune »). Le millésime voyage avec la
   valeur, écrit une fois (point unique).

**Vérification (Phase 3) :**
- **Golden 119/119** — statut_anc n'est pas un champ golden ; aucune ancre des 3 communes cassée.
- **4 documents** servent le statut : banquier Salazie rend « INTÉGRALEMENT ANC » + « Sourcé commune »
  + « données 2023 » + « Corroboré INSEE ». Front `tsc` exit 0.
- **Grep** : aucune valeur ANC ni code commune EN DUR dans `anc_service` (la liste vient de la table,
  du seed) ; la source/millésime viennent de `data_sources` + table.
- **Suite 1549 passed, 0 failed** ; `test_anc_service` 4 passed (dont le nouveau test source_commune :
  échelle + millésime dits ; une commune < 100 % NE bascule pas).
- **Recette** : Salazie / La Plaine-des-Palmistes / Petite-Île → `source_commune`, échelle commune,
  millésime « Chronique n°149 — données 2023 », corroboration INSEE (94-98 %).

**Interdits respectés** : Sourcé sur source primaire vérifiée (Office de l'eau + INSEE + CIREST/CIVIS) ;
millésime = date amont (2023), jamais l'ingestion ; PAS de branche parallèle à `anc_service` ; échelle
commune DITE (jamais présentée comme parcellaire) ; rien inventé.
