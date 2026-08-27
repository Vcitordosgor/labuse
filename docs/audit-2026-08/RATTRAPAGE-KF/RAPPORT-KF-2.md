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

**Remplacements évalués (NON ingérés, per mandat).**
- **Cartofriches (Cerema)** — inventaire national des friches, **Licence Ouverte 2.0**, téléchargeable
  sur data.gouv.fr, MAJ 15/06/2026. **974 couvert via l'AGORAH** (~**340 friches urbaines bâties**,
  ~30 ha, relevé terrain 2025 dans les périmètres ORT). MAIS c'est un signal de **friches / foncier
  mutable**, **pas** de la commercialisation VEFA — un autre objet. Candidat sérieux pour une future
  couche « foncier mutable 974 », hors périmètre de ce mandat.
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

## FINDINGS
- **KF-101** (L0-a) — Le 2025 versionné n'est pas encore dans `pm_proprietaires_millesimes` (l'ingestion
  M2 précède sa publication amont). Le millésime servi 2025 vit dans `parcelle_personne_morale`. À unifier
  en L1 **sans écraser le servi**.
- **KF-102** (L0-a) — Pic de changements SIREN 2019→2020 (12 184) très supérieur aux années suivantes :
  probable discontinuité de source (complétude SIREN croissante), pas un afflux de ventes. Le diff le dit
  comme un constat ; ne jamais l'interpréter comme des transactions.
- **KF-103** (L0-b) — ECLN hors champ pour le 974 (métropole seule + jamais à la parcelle). Conclusion
  ferme, L2 annulé. Substituts Cartofriches (974 via AGORAH ~340 friches) et Orfel (foncier d'État, DROM)
  évalués mais = signaux adjacents, pas VEFA.
