# RAPPORT — RATTRAPAGE KELFONCIER 2/2 : INGESTION

Branche `feat/rattrapage-kf-2`. Régime autonome, commits par lot L0→L3. Doctrine : Sourcé/Estimé/Absent,
zéro faux positif, fraîcheur = date source amont, **aucune donnée inventée ni maille silencieusement
changée**. Une source absente/vide sur le 974 est une **conclusion écrite**, pas un trou à combler.

---

## L0 — ENQUÊTE DE DISPONIBILITÉ (écrite AVANT tout code)

### (a) DGFiP — Fichiers des parcelles des personnes morales, millésimes 2019→2025 — **VERT**

**Où / licence / cadence.** Plateforme **data.economie.gouv.fr**, jeu
`fichiers-des-locaux-et-des-parcelles-des-personnes-morales`, **Licence Ouverte 2.0**. Publication
**annuelle** (un fichier « situation au 1ᵉʳ janvier » par millésime). Vérifié en direct ce jour via
l'API catalogue (`/api/v2/.../attachments`).

**Millésimes réellement disponibles.** Les pièces jointes existent en ligne pour **2019, 2020, 2021,
2022, 2023, 2024 ET 2025** (chaque année scindée en deux tranches de départements ; le 974 est dans la
tranche haute — `..._dept_62_a_976` / en 2025 `..._dpts_57_a_976`). Le **2025 est désormais publié**
(il ne l'était pas au moment de l'ingestion M2 du 12/07/2026 : `MILLESIME_ATTACHMENTS` s'arrête à 2024).

**Déjà en base (échantillon RÉELLEMENT examiné, pas une page de doc).** La table versionnée
**`pm_proprietaires_millesimes`** (clé `(millesime, idu)`) contient **461 570 lignes** couvrant
**2019→2024**, importées le 12/07/2026, `url_source` = data.economie.gouv, chacune avec **siren +
dénomination + forme + groupe à 100 %** :

| millésime | parcelles 974 | SIREN | dénomination | communes |
|---|---:|---:|---:|---:|
| 2019 | 72 709 | 100 % | 100 % | 24/24 |
| 2020 | 74 029 | 100 % | 100 % | 24/24 |
| 2021 | 76 270 | 100 % | 100 % | 24/24 |
| 2022 | 78 056 | 100 % | 100 % | 24/24 |
| 2023 | 79 345 | 100 % | 100 % | 24/24 |
| 2024 | 81 161 | 100 % | 100 % | 24/24 |
| **2025** (servi, `parcelle_personne_morale`) | 82 701 | oui | oui | 24/24 |

**Couverture 24 communes** : complète tous les millésimes. **Poids** : le ZIP amont est national
multi-départements (plusieurs centaines de Mo) ; le sous-ensemble **974 extrait** = ~72–83k lignes/an
(le module `ingestion/pm_millesimes.py` télécharge le ZIP, met en cache disque, et n'extrait que le
membre 974).

**Structure d'une année sur l'autre — stable, et les écarts sont CONSTATÉS, jamais devinés.** Le loader
existant vérifie l'entête (`_sniff_header` : **24 colonnes attendues, tout écart est LEVÉ**). Diffs réels
documentés dans le code : 2021-2023 = membre `.txt` latin-1, entête quotée, **département éclaté**
(`Département='97'` + `Code Direction='4'`), groupe en code nu ; 2024/2025 = membre `.csv`,
`Département='974'`, groupe parfois libellé. Positions de colonnes **identiques**. **Code direction / 97
stable** : après normalisation, **100 % des `idu` commencent par `974`** et font **14 caractères** sur
les 461 570 lignes.

**Signal du diff annuel — réel.** Changements de SIREN propriétaire d'un millésime au suivant (parcelles
présentes les deux années) : **2019→2020 : 12 184** · 2020→2021 : 6 455 · 2021→2022 : 1 894 ·
2022→2023 : 2 290 · 2023→2024 : 1 611. Le pic 2019→2020 est probablement une **discontinuité de source**
(SIREN mieux renseignés au fil des millésimes), pas 12k transactions — à dire dans la fiche (le diff est
un CONSTAT, il n'affirme pas une vente). Les années récentes (~1 600–2 300 parcelles/an qui changent de
PM) sont un signal net pour un promoteur.

**Conclusion (a) : VERT.** → **L1 est construit.** Base déjà présente (2019-2024) ; on complète avec le
**2025** désormais publié, dans la MÊME table versionnée, **sans jamais toucher** la table servie
`parcelle_personne_morale`.

### (b) ECLN — Commercialisation des logements neufs (VEFA, programmes) — **ROUGE pour le 974**

**Enquête, pas fichier ; métropole seule.** L'ECLN est une **enquête** trimestrielle du SDES sur les
programmes de **5 logements et plus destinés à la vente**. La méthodologie officielle SDES l'énonce
noir sur blanc : **« L'enquête est réalisée en France métropolitaine »** — les **DOM sont hors champ**,
974 compris. Le jeu national data.gouv est **national-only trimestriel** ; le jeu départemental ne porte
donc pas le 974 (hors champ d'enquête). Diffusion sous secret statistique (`nd` = non diffusible) qui
viderait de toute façon les mailles fines. Et l'ECLN n'est **jamais à la parcelle** — c'est un agrégat
d'enquête.

**Conclusion (b) : ROUGE.** Le 974 n'est **ni à la parcelle ni à la commune** exploitable (hors champ
métropole). → **L2 est ANNULÉ** (voir plus bas), pas contourné.

**Remplacements évalués (NON ingérés dans ce mandat, per consigne).**
- **Cartofriches (Cerema)** — inventaire national des friches, **Licence Ouverte 2.0**, MAJ 15/06/2026.
  **974 couvert** (373 friches, rattachement IDU exact via refcad). **DÉJÀ INGÉRÉ dans le produit** :
  le catalogue le porte en source `connecte` (couche `spatial_layers kind='friche'`, endpoint
  apidf-preprod.cerema.fr). C'est un signal de **friches / foncier mutable**, **pas** de la
  commercialisation VEFA — un autre objet, déjà présent : rien à ré-ingérer, aucun substitut VEFA.
- **Orfel (foncier de l'État pour le logement, DGFiP)** — inventaire temps réel du foncier d'État
  cessible pour le logement, **DROM inclus** (donc 974). MAIS **~335 sites au national** (foncier d'État
  seul) → sous-ensemble 974 minuscule, objet très spécifique. Pas un substitut VEFA.

Aucun des deux ne remplace l'ECLN : ce sont des signaux fonciers **adjacents**. Recommandation : si une
couche « foncier mutable » est voulue un jour, **Cartofriches/AGORAH** est le meilleur candidat ouvert
sur le 974 — mais c'est un **mandat distinct**, pas un rattrapage VEFA. L2 reste annulé.

---

## DÉCISION DE PORTÉE (issue de L0)
- **L1 — GO** : historique propriétaire par millésime + diff annuel (constat, hors scoring, PM seulement).
- **L2 — ANNULÉ** : ECLN hors champ 974 (métropole seule, jamais à la parcelle). Remplacements évalués,
  non ingérés.
- **L3 — GO** (pour la source L1) : registre des sources + procédure de rafraîchissement.

---

## L1 — HISTORIQUE DES PROPRIÉTAIRES PAR MILLÉSIME + DIFF ANNUEL — **FAIT**

**Données versionnées, servi jamais écrasé.** `proprietaire_historique.py` lit la table versionnée
`pm_proprietaires_millesimes` (2019→2024, déjà en base) UNIE à la volée au millésime **2025 servi**
(`parcelle_personne_morale`, **lecture seule**). Le millésime est une COLONNE ; le `NOT EXISTS` garde
contre tout doublon le jour où un 2025 versionné serait ingéré. **Frontière versionné→servi validée** :
le diff 2024→2025 (Saint-Paul : 116 changements) est *inférieur* aux années antérieures (253, 267) —
l'union ne fabrique pas de faux changements ; le SIREN « U… » (variant légitime) est présent dans les
DEUX tables (~12-13 %), pas un artefact de bord.

**Diff = CONSTAT, jamais interprétation.** Pour chaque parcelle : la timeline (millésime → dénomination
+ SIREN, avec la situation « 1ᵉʳ janvier AAAA ») et les CHANGEMENTS consécutifs (avant → après). Ex.
réel (parcelle 97401000AL0815) : 2023→2024, `BICEPHALE FONCIERE IMMOBILIERE` → `REUNION AMENAGEMENT
FONCIER ET INVESTISSEMENT IMMOBILIER`. Aucune phrase « prépare une opération » ; une note de lecture
rappelle qu'un changement n'affirme pas une vente et **n'entre pas au scoring**.

**Affichage.**
- **Fiche parcelle** (`proprietaire_historique` dans `_q_v2_fiche` → `ProprietaireHistorique.tsx`, tiroir
  Propriétaire) : les changements en tête, la timeline dépliable, la source + la note de constat.
- **Fiche commune** (`acquisitions_pm` dans `/communes/{c}/contexte` → `ContextePanel`) : « Acquisitions
  PM récentes » — le volume S'Y PRÊTE (Saint-Paul : **773** changements depuis 2022), donc servi :
  « N sur M » à la **maille COMMUNE** (dite), aperçu borné à 8, du plus récent au plus ancien.
- Endpoints : `GET /proprietaires/{idu}/historique`, `GET /proprietaires/acquisitions?commune=`.

**RGPD** : ces fichiers ne portent que des personnes MORALES — aucune personne physique n'entre, sous
aucune forme. **Hors scoring** : l'historique s'affiche, il ne pondère rien. Verrou :
`tests/test_proprietaire_historique.py` (timeline unifiée, diff constat, acquisitions n_total, PM-only,
endpoints, non-couvert). 5/5.

## L2 — PROGRAMMES NEUFS / VEFA — **ANNULÉ** (L0-b rouge)

ECLN hors champ pour le 974 (enquête métropole seule, jamais à la parcelle). Rien n'est ingéré, aucune
maille silencieusement changée, aucune valeur départementale répartie sur les communes. Substituts
(Cartofriches déjà ingéré, Orfel) évalués : signaux fonciers adjacents, pas de la commercialisation
VEFA. **Conclusion écrite, lot fermé.**

## L3 — FRAÎCHEUR ET EXPLOITATION — **FAIT**

La source « DGFiP — parcelles des personnes morales » (déjà au catalogue) est **enrichie** : `source_cadence
= annuelle`, `source_horizon_at = 2025-01-01`, millésime « Panel millésimes 2019→2025 », `last_sync_at`
posé à la **vraie** date d'ingestion (`max(date_import)` = 2026-07-12, jamais inventée), notes = panel +
diff + garde-fou KF-102. Le dashboard admin/Sources affiche donc la cadence et le badge « à mettre à jour ».
Commande de rafraîchissement **`labuse ingest-pm-millesimes`** (idempotent, table versionnée jamais la
servie, repose la fraîcheur ; `--fraicheur-seule` pour le seul badge) — documentée dans
`docs/EXPLOITATION-CRON.md` (cadence annuelle, à la main). L'attachment 2025 (publié en amont) est ajouté
à `MILLESIME_ATTACHMENTS` pour que la commande puisse le charger si voulu.

---

## FINDINGS
- **KF-101** (L0-a) — Le 2025 versionné n'est pas encore dans `pm_proprietaires_millesimes` (l'ingestion
  M2 précède sa publication amont). Le millésime servi 2025 vit dans `parcelle_personne_morale`. À unifier
  en L1 **sans écraser le servi**.
- **KF-102** (L0-a) — Pic de changements SIREN 2019→2020 (12 184) très supérieur aux années suivantes :
  probable discontinuité de source (complétude SIREN croissante), pas un afflux de ventes. Le diff le dit
  comme un constat ; ne jamais l'interpréter comme des transactions.
- **KF-103** (L0-b) — ECLN hors champ pour le 974 (métropole seule + jamais à la parcelle). Conclusion
  ferme, L2 annulé. Substituts Cartofriches (974, 373 friches, DÉJÀ ingéré) et Orfel (foncier d'État, DROM)
  évalués mais = signaux adjacents, pas VEFA.
- **KF-104** (L1) — Les « acquisitions récentes » sont servies à la **maille COMMUNE** (dite à l'écran),
  pas « secteur » cadastral fin : le volume par commune s'y prête (Saint-Paul 773 depuis 2022) et la
  lecture reste claire. La maille est affichée, jamais changée en silence.

---

## VÉRIFICATIONS FINALES
- **Gardées** : la suite touchée est verte (`test_proprietaire_historique.py` 5/5, `test_pm_millesimes.py`
  4/4). **Golden inchangé** : `git diff 5a3e3a9b..HEAD` ne touche **aucun** fichier de scoring/zonage/run/
  golden (uniquement fiche/contexte, ingestion, catalogue, doc) → la dérive golden reste celle, PRÉ-EXISTANTE
  et branch-indépendante, déjà documentée en KF-1 (run base `q_v11_m137` vs golden `q_v10_m129` + libellé
  zonage M128-2-J). Ce mandat n'introduit aucun écart golden.
- **tsc** 0 · **build** ✓ (frontend).
- **Suite au niveau de la base — prouvé par worktree** : worktree détaché sur `5a3e3a9b` (commit du mandat)
  = **1868 passed, 0 failed** ; sur la branche = **1874 passed, 0 failed** (+6 = les tests L1). Aucune
  régression.
- **[KF-TEST]** : le test L1 s'auto-nettoie (fixture `yield` + DELETE). Base `labuse` de dev : les données
  servies sont les millésimes DGFiP réels, pas des objets de test.
