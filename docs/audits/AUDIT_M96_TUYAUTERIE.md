# AUDIT M96 — LA TUYAUTERIE (source → surface, surface → source)

Audité le 2026-08-17, sur la base locale, run servi `q_v9_m81` (config/served_run.txt).
Graphe machine : `docs/audits/AUDIT_M96_TUYAUTERIE.json` (50 sources, 18 surfaces, 11 verdicts).
Ce rapport MESURE — aucun correctif appliqué, les arbitrages restent à Vic.

## Le compte

| verdict | n | détail |
|---|---|---|
| **FANTÔME** | **0** | aucune surface ne sert une donnée hors catalogue (3 candidats instruits, tous réfutés) |
| **SURFACE ASSOIFFÉE** | **0** | le cas type (ANC absent des PDF) est réglé M73-C/D et gardé par le test de non-contradiction (4 docs) |
| **TUYAU PÉRIMÉ** | **0** | aucune surface ne lit une table ancienne alors qu'une plus récente existe (le cas M86-B est résolu — hiérarchie unique dans `anc_service`) |
| **AMONT EN AVANCE** | **3** | Cadastre Etalab, BAN, BODACC (faits sondés en direct le 17/08) |
| **DOUBLE TUYAU** | **2** | charge foncière banquier (latent) ; permis du brief (assumé, à échéance) |
| **TUYAU MORT** | **1** | `dvf_mutations_histo` (échelle table, usage entraînement assumé) |
| **SAIN** | **50/50 sources affichées** | dont 9 avec réserves documentées (proxies, dettes de doublons, amont mort ABF) |

Hors grille, **le finding le plus visible pour l'utilisateur** : une source **SERVIE MAIS
MASQUÉE** (Office de l'eau). Et deux écarts d'énoncé : le mandat disait 49 sources
(mesure : 50) et 29 outils (registre : 28).

---

## 1. Les findings, triés par gravité

### 1.1 SERVIE MAIS MASQUÉE — Office de l'eau (le masquage M87 est périmé de fait)

Le cas exact que le mandat demandait de re-vérifier : « les MORTES de M86 — la liste a
bougé ». Elle a bougé.

- M87 P0 a masqué « Office de l'eau Réunion — Chroniques de l'eau » de la page Sources
  (`sources_catalog.py:12-14`), au motif « lue uniquement par un contrôle QA ».
- M95 a renversé cet état : `anc_office_eau_commune` (seed versionné
  `data/anc/office_eau_chronique_149_2023.csv`, `anc.py:322-357`) est **servie** à la
  fiche — badge « Sourcé · commune » pour les 3 communes 100 % ANC — et dans les
  4 documents (`anc_service.py:50-81`).
- Le millésime M95 (« Chronique n°149 — données 2023 », mesuré en base) est écrit sur la
  ligne `data_sources` **masquée** (`anc.py:352`).

Conséquence : l'utilisateur voit la source citée en fiche, mais elle est absente de la
page Sources et du compteur (50). La fiche et le catalogue affiché ne racontent pas la
même chose.

### 1.2 AMONT EN AVANCE — 3 faits (sondés en direct le 17/08, sondes radar.py, zéro téléchargement)

| source | amont publié | ingéré | lecture |
|---|---|---|---|
| **Cadastre Etalab** (assiette `parcels`) | artefact latest **2026-07-02** | édition **2026-06** | une édition cadastrale plus récente existe et n'est pas ingérée. Mode « grande passe » (cascade gelée) : la réingestion est une décision, pas un cron — mais le fait est là. |
| **BAN** | artefact 974 **2026-08-17** | **2026-07-11** | le cycle mensuel « le 5 » (deploy/cron.d/ban) n'a pas joué sur cette base depuis le 11/07. |
| **BODACC** | parution **2026-08-16** | sondé jusqu'au **2026-08-13** | 3 jours de parutions non sondées ici. Nuance obligatoire : l'horizon table (06/08) ne porte que sur les ~12,6k SIREN suivis, événements rares (`fraicheur.py:43-47`) — aucune annonce manquante prouvée pour ces SIREN. |

À l'inverse, **DVF** (amont 18/05, prochaine livraison 2026-10), **SITADEL** (amont
28/07, sondé 14/08) et **DPE** (amont 12/08, sondé 13/08) sont ingérés APRÈS la dernière
publication amont : à jour côté ingestion. Le retard DPE (données 974 au 21/07, 27 j >
seuil 14 j) est DANS la donnée amont et il est dit à l'écran — conforme M84, aucun seuil
à desserrer.

Le thermomètre lui-même : `source_radar` n'a pas re-sondé depuis le **22/07** sur cette
base (cron VPS hebdo) — les badges « version vérifiée » de la page Sources datent de ce
passage.

### 1.3 DOUBLE TUYAU (latent) — la charge foncière du banquier

`briques_pdf.py:350-367` : le point de calcul unique documenté est la charge du bilan à
rebours (24 %) ; si `compute_bilan_servi` échoue (`briques_pdf.py:317-319`), repli
**silencieux** sur `score_e.charge_supportable` (21 %). Le drapeau `charge_du_bilan`
est calculé (`:367`) mais **aucun gabarit ne le lit** (grep : une occurrence, sa
définition). Le lecteur du document ne peut pas savoir quelle charge il lit. Impact
conditionnel (uniquement si le bilan est absent), mais les deux calculs coexistent sur
le même document.

### 1.4 DOUBLE TUYAU (assumé) — les permis du brief

La ligne « permis sur vos secteurs » du brief lit `sitadel_permits` en direct
(`events.py:963-965`) quand la même donnée transite par `event_log` via
`evaluer_suivis` (`events.py:285-341`) pour la cloche. Doublon d'appoint documenté à
l'époque où les crons VPS n'étaient pas actifs (M85/M87) — les crons le sont
(deploy/cron.d/notifications), l'appoint est toujours là.

### 1.5 TUYAU MORT (échelle table) — `dvf_mutations_histo`

DVF 2014-2020 (M3.5). Unique lecteur : le dataset d'entraînement du modèle P
(`scoring/p_model/ext_sql.py`). Aucun lecteur servi. La source DVF est servie par
ailleurs (`dvf_mutations_parcelle`) ; ce sous-tuyau historique n'alimente aucune
surface. Usage entraînement plausiblement voulu — à trancher (assumer ou brancher).

### 1.6 FRAÎCHEUR au robinet — 2 écarts catalogue↔donnée (impact servi nul, mesurés)

« Trois dates, une seule vérité » : pour BODACC et DPE, la vérité a divergé **dans le
catalogue** de cette base :

| source | horizon catalogue | horizon table (date_sql) | last_sync |
|---|---|---|---|
| BODACC | 2026-07-02 | 2026-08-06 | 2026-08-13 |
| DPE | 2026-07-03 | 2026-07-21 | 2026-08-13 |

Cause : les ingestions locales du 13/08 ont tourné **sans** `fraicheur-derives`
(`persist_millesime`, `fraicheur.py:282-314`), pourtant chaîné dans les crons VPS
(`deploy/cron.d/bodacc`, `dpe`). Impact servi **nul aujourd'hui** : la page Sources
calcule `derniere_donnee` en LIVE (`fraicheur.etat_sources`, date_sql), et le seul
lecteur servi de `source_horizon_at` est `_fraicheur_couche` pour DVF
(`modules.py:863`), dont l'horizon est juste. Les 8 autres lignes suivies concordent
(SITADEL, DVF, BAN, Sudocuh, ortho ; GPU/Géorisques NULL par doctrine
`HORIZON_NON_AMONT`, `fraicheur.py:141` ; CatNat sans ligne catalogue, no-op explicite).

### 1.7 Écarts d'énoncé — 50 sources, 28 outils

- Le mandat annonce **49** sources ; `WHERE_AFFICHEES` en rend **50** (requête au
  JSON ; M87 annonçait 50 aussi).
- Le mandat parle de **29** outils ; `registry.ts:38-105` en compte **28**.

---

## 2. Fraîcheur amont — le reste du tableau (Phase 3.5)

**Présomptions par cadence** (pas de sonde — dits comme présomptions, pas comme faits) :

| source | ingéré | cadence producteur | présomption |
|---|---|---|---|
| Sudocuh | état au 31/12/2024 | annuelle | un état au 31/12/2025 a pu paraître courant 2026 — non vérifié ; le geste trimestriel `scripts/veille_plu_check.py` couvre la chair servie (YAML) |
| Contours IRIS | géographie 2024 | annuelle (IGN) | une géographie 2025/2026 existe probablement |
| Filosofi | millésime 2021 | annuelle, décalée ~3-4 ans | un millésime 2022+ a probablement paru (data-gap assumé au catalogue) |
| Inventaire SRU | CSV du 18/12/2025 (inventaire 01/01/2024) | annuelle DHUP | un inventaire au 01/01/2025 a pu paraître |
| RP2022 EGOUL | publié 16/10/2025 | annuelle | le RP2023 paraîtrait ~fin 2026 — vraisemblablement pas encore paru |
| QPV 2024 / BD ORTHO 2025 | — | générationnelle / re-survol 3-4 ans | à jour par nature |

**Non vérifiables, assumés** : GPU/PLU et Géorisques (révisions irrégulières, détection
seule — cascade gelée), couches DEAL Lizmap (HEAD 501), ABF (endpoint amont
décommissionné — HEAD 404, base figée au 05/07/2026, documenté `abf_merimee.py:40`),
Cartofriches (403), WFS Géoplateforme (400), ODS Région, textes/extractions (RTAA, PLH),
API vivantes sans notion d'édition (PVGIS, LiDAR, RGE ALTI, OSM, SIRENE-DINUM). Liste
complète et preuves `source_radar` au JSON.

---

## 3. Candidats instruits et écartés (preuve à l'appui)

Sept anomalies candidates remontées pendant l'audit ont été contre-vérifiées et
**réfutées** — elles ne doivent pas ressortir comme dettes :

| candidat | réfutation |
|---|---|
| TUYAU MORT Géorisques ICPE / cavités / MVT | couches cascade étage 1 servies (`etage1.py:206-229`) + dossier flash > Risques (`flash/data.py:311-346`) + liste ICPE de proximité (`flash/data.py:337-343`). MVT : flag affiché, 0 point — anti double-compte PPR, design. |
| FANTÔME SRU | source « Inventaire SRU (DHUP) » au catalogue ; écrivain `scripts/ingest_sru.py:57` ; lecteurs servis : flash, Mode bailleur, Comparateur, ZAN, premium, projets. |
| FANTÔME PVGIS | ligne `data_sources` présente (mesuré, last_sync 11/07) ; servi via `viabilisation_build.py:131-154` (point unique, information jamais scorée). |
| RTAA DOM hors catalogue | ligne `data_sources` présente (mesuré) ; servi contexte commune + premium. |
| ORPHELIN Vérif procédure (table `commune_plu_procedures`) | la route lit le **registre veille_plu** (point unique YAML), `modules.py:1149-1200` — pas de table morte. |
| ROUTE MORTE Quoi de neuf O10 | `blocB.tsx:329` lit `/events?limit=100` (event_log) — vivant ; les 6 cassés de M82 sont réparés (refs au JSON). |
| DOUBLE TUYAU parcel_anc/zone_anc vs anc_maille_taux (cas M86-B) | résolu : hiérarchie unique dans `anc_service.statut_anc` (parcellaire → commune M95 → secteur M88 → Absent) ; `proba_anc` jamais lu servi (dormant assumé M88, signal `anc_mutation` seul). |

---

## 4. L'état sain, en deux mots

- **Points d'appel uniques tous respectés** : DVF/permis (`marche_service`, M73-B),
  ANC (`anc_service`), Mode B (`compute_mode_b`), bilan (`compute_bilan_servi`),
  verdict (`verdict_servi`), plan ortho (`plan_situation`), limites
  (`export_commun.limites_document`).
- **Run servi épinglé partout** : `q_v9_m81` via `Q_A_RUN_LABEL`
  (config/served_run.txt), fail-close (RuntimeError si absent, front refuse de booter
  sans `VITE_RUN_LABEL`).
- **Millésimes centralisés** (doctrine M86) : SourceDrawer, page Sources, plan ortho
  premium (`app.py:2923-2924`) lisent `data_sources.source_millesime` — aucun millésime
  en dur trouvé côté surfaces (les libellés statiques restants — Filosofi 2021, RPLS —
  correspondent au millésime réellement ingéré).
- **Réserves documentées et badgées** (pas des anomalies) : proxies SAR/SAFER/ENS/OCS GE,
  Sudocuh curée, couverture zonage ANC 4/24 communes, doublons de lignes forêts (162) et
  OCS GE (1 607) — dette backlog déjà actée au seed.
- **Notifications** : registre unique, 5 types, producteurs tracés ; `saved_searches`
  vide (aucune recherche sauvegardée par personne — état d'usage) ; `_veilles_match`
  ne tourne qu'à la bascule de run (design bascules), `evaluer-veilles` est bien au
  cron.
- **Copilote v2** : les 7 outils du routeur délèguent tous à un point de calcul
  existant, verrou anti-invention actif — aucun recalcul local, aucune valeur en dur.

## Interdits respectés

Aucun correctif appliqué, même évident. Chaque verdict porte sa preuve fichier:ligne ou
sa requête. Les surfaces sont nommées une à une (JSON). Pas de merge.
