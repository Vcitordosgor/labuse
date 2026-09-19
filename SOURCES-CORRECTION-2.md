# SOURCES-CORRECTION-2 — Les trois restes

**Branche** `feat/sources-audit-1` — étape 0 : `c478d2e2` (HEAD après SOURCES-CORRECTION-1). Un commit par
lot, branche poussée, aucun merge. Gates : `tsc -b` vert, `labuse circuit verrous -w G8` vert.

---

## Lot 1 — les deux statuts, tranchés

### `cadastre_epoque` → **`interne`** (nouveau statut) : hors vitrine CLIENT, visible au Circuit ADMIN

Décision : cadastre_epoque ne sert qu'à **recaler la géométrie des permis Sitadel** (aucune surface
client) → elle **sort de la vitrine**, mais reste **inspectable dans le Circuit admin avec son rôle
déclaré** — pas masquée comme les retirées. Aucun statut existant ne disait « référentiel interne » :
j'en ai **ajouté un** (`DataSourceStatus.INTERNE = "interne"`), première classe comme `hub`/`partenariat_requis`.

- **`enums.py`** — `INTERNE = "interne"` (ingéré et LU par la pompe, rien au client ; la note DOIT nommer le rôle).
- **`circuit_verrous.py`** (V2b `analyse_catalogue`) — branche `elif statut == "interne"` : accepté hors
  vitrine **à condition que la note nomme le rôle** (sinon violation) — même discipline que `partenariat_requis`.
- **`api/dashboard.py`** (`_assembler_reservoirs`, ce que sert le Circuit admin) — filtre passé de
  `WHERE_AFFICHEES` à **`(WHERE_AFFICHEES) OR status='interne'`** : le Circuit montre désormais **vitrine ∪
  référentiels internes**. Les compteurs CLIENT (`WHERE_AFFICHEES` : `/sources`, accueil, `flux.construire_flux`,
  V2a) sont **inchangés** — le split des deux audiences est là.
- **`seed_sources.py`** — entrée cadastre_epoque : `status=S.INTERNE` + note refaite qui **nomme le rôle**
  (`cadastre_historique` lue par `ingestion/cadastre_historique.py:rattacher_par_geometrie` pour recaler
  Sitadel). **DB** : `UPDATE status='interne'` + même note.

### `sudocuh` → **reste en vitrine** (inchangé)

Elle alimente le modèle candidat `q_v14` (`anciennete_plu`), **visible dès la bascule** du run servi. On la
garde `connecte` : la sortir puis la rentrer à la promotion de `q_v14` serait du yo-yo. Aucune modification.

### Preuve

- **Vitrine 93 → 92** (client). **`V2a` OK — 92 = 92 = 92** (vitrine SQL = prédicat Python `est_affichee` =
  page `flux.construire_flux`) ; **`V2b` OK** (interne accepté, rôle nommé) ; catalogue validé.
- **cadastre_epoque dans le Circuit ADMIN** : `_assembler_reservoirs` = **93 réservoirs, cadastre_epoque
  présent** (carte réservoir rendue, mode one_shot) ; **`flux.construire_flux` (client) = 92, cadastre_epoque
  ABSENT**. Le référentiel interne est visible à l'admin, invisible au client — exactement le partage demandé.
- **`verrous -w G8` exit 0, tout va bien** : ajouter un statut a demandé **4 listes fermées** cohérentes —
  `enums.py` (l'enum), V2b `analyse_catalogue` (accepte + exige le rôle), **`STATUTS_ADMIS` de G1** (la
  garantie « liste fermée » — G1 a cassé au premier essai, réparé ici), et `_assembler_reservoirs`
  (le Circuit). `test_g1_statut_hors_liste_fermee_casse` (qui fige la liste) mis à jour avec `interne` → **passe**.
- `tsc -b` : le front Circuit est data-driven (rend la carte réservoir telle quelle) → aucun fichier front touché.
- *Les autres tests rouges (les 4 « morts » d'avant CRON-1 + `test_g2_signature_dpe`, périmé par la
  ré-ingestion DPE du mandat précédent qui asserte encore `dpe_ademe quasi_vide` + la composition
  25 verrous/garanties) sont réconciliés au **lot 3** (« pytest sans échec »).*

---

## Lot 2 — l'attribution `anru`

SOURCES-CORRECTION-1 lot 2 avait fait passer `deal_wms_wfs` en `hub`, mais les 8 lignes
`spatial_layers kind='anru'` pointaient encore ce hub par leur `data_source_id` (héritage M74), alors
que le registre (`RESERVOIR_TABLES`) déclare le réservoir **`npnru`**. La source RÉELLE de la couche
était donc un `hub` (hors vitrine) → l'audit couche↔source tombait à **55/56** (check 2 : « la source
réelle est-elle `connecte` ? »).

**Corrigé** — `scripts/correction2_anru_raccord.py` (idempotent, ré-exécutable, rattachement **par nom**,
comme les 3 provenances fausses de COUCHES-REGISTRE-2 : axe_structurant/ligne_ht/tva_primo) : les 8 lignes
`anru` passent de `data_source_id` = « DEAL Réunion (WMS/WFS) » (hub) à « NPNRU (DEAL Réunion / ANCT) »
(connecte, id résolu par nom). **Aucune géométrie touchée** (colonne `data_source_id` seule), aucune tuile
reconstruite. `deal_wms_wfs` devient un **hub réellement vide** (ne possède plus aucune couche).

### Preuve
- `scripts/audit_couches_registre.py` : **CHECK 1 (Registre) 56/56 | CHECK 2 (Réservoir réel) 56/56** (le
  `real` d'`anru` est désormais « NPNRU … [connecte] ×8 »). Idempotence vérifiée : ré-exécution = 0 ligne déplacée.
- `verrous -w G8` exit 0 ; `tsc -b` : aucun fichier front touché (le script est backend/DB, le registre code
  déclarait déjà npnru — rien à changer côté `RESERVOIR_TABLES`).

---

## Lot 3 — les tests morts (pytest sans échec)

« Remettre sur les valeurs réelles, ou retirer si l'invariant est porté par un verrou. » Aucun n'est
retiré : chaque invariant reste valide — seule la **valeur** figée avait dérivé. Pour chacun, le geste :

| Test | Ce qu'il affirmait (périmé) | Geste (dire lequel) |
|---|---|---|
| `test_circuit1_lot6` (renommé `test_agent_source_surface_et_plafond`) | « `désactivé` in agents-sources.cadence » | **Valeur réelle** : CRON-1 registre agents-sources en cron **du dimanche** ; l'invariant « jamais de dépense par défaut » est désormais porté par le **plafond `LABUSE_AGENT_PLAFOND_EUR` (défaut 0 €)**, pas par une cadence « désactivé ». Asserte cadence=`hebdo (dim)` + titre « plafonné ». |
| `test_circuit_p_lot1::test_detail_reservoir…` | `len(jobs_eau) == 13` | **Valeur réelle** : `TOUCHE_EAU` = **9** jobs eau (CRON-1 a refait le registre). 13 → 9. |
| `test_sentinelle::…_64_sources…` | `raison ⊆ SOURCES` casse sur `communes_ign` | **Valeur réelle** : `communes_ign` est une source **réelle** mais seedée par le **référentiel embarqué** (`scripts/registre2_raccord_db.py`), hors de la liste `SOURCES` — comme les 2 doublons déjà exceptés. Admise. |
| `test_circuit2_lot5::test_couches_info…` | `set(couches-info) == COUCHE_PAR_CLE_FRONT` | **Valeur réelle** : le « i » couvre **les 56 kind du tuyau** (`couches_tuyau.registre`), pas le pont `COUCHE_PAR_CLE_FRONT` (hérité, 38 clés aux anciens noms V1). Asserte contre le registre tuyau ; `parcelles` → `limites_parcelles`. **+ correctif endpoint** (`app.py`) : fabrication par **défaut** « reconstruite à la bascule (tuyau vectoriel) » pour les kinds sans cid — sinon 18 couches affichaient une fabrication VIDE dans leur « i ». |
| `test_garanties::test_g2_signature_dpe…` | `dpe_ademe quasi_vide is True` | **Valeur réelle** : SOURCES-CORRECTION-1 a rempli DPE (16 → 1123) → `quasi_vide` **False**. Devient un **garde-fou anti-régression** du correctif DPE. |
| `test_garanties::test_g2_vert…` | « `dpe_ademe` in preuve » (la vide nommée) | **Valeur réelle** : DPE rempli → G2 mesure **0 source vide**. Asserte « 0 source » ; la promesse « une vide est nommée » reste portée par `verrou_g2`. |
| `test_garanties::test_les_24…` | ids = 18 verrous + 7 garanties (25) | **Valeur réelle** : CRON-1 lot 2 a ajouté **G8** → 18 verrous + **8** garanties = **26**. + G8. |
| `test_garanties::test_g1_statut…` (déjà au lot 1) | `STATUTS_ADMIS` figée sans `interne` | **Valeur réelle** (lot 1) : + `interne`. |

### + 3 rouges pré-existants découverts par la suite COMPLÈTE (hors des 4 nommés, d'autres mandats)

Mon rapport SOURCES-CORRECTION-1 n'avait listé « 4 échecs » qu'à partir de sous-ensembles ; la suite
ENTIÈRE en révèle **3 de plus**, tous pré-existants (rien de mon fait SC-2 — je n'ai touché aucun de ces
fichiers), qu'il faut aussi verdir pour « pytest sans échec » :

| Test | Origine | Geste |
|---|---|---|
| `test_lot6_porte::test_deploy_sh_joue_les_verrous_avant_tout` | CRON-1 lot 3 a réécrit `deploy.sh` (refus d'un verrou **BLOQUANT** — G8 non bloquant). | **Valeur réelle** : le test asserte le texte réel du script (`un verrou BLOQUANT est cassé`). |
| `test_lot6_porte::test_verrous_md_se_lit_sans_le_code` | COUCHES-TUYAU a ajouté le verrou **V7a** (tuiles) sans documenter `docs/CIRCUIT/VERROUS.md`. | **Doc remise à jour** : ligne V7a ajoutée à VERROUS.md (le document pour Vic liste bien chaque verrou joué). |
| `test_reparations1_lot2::test_graphe_exact_dans_les_deux_sens` | 2 lecteurs de MACHINERIE non déclarés au graphe G6 : `api/couches_tuyau.py` (lit `ortho_detections`), `cascade/layers/fiche_couches4.py` (lit `parcels`). | **Arbitrage écrit** : ajoutés à `LECTEURS_ASSUMES_G6` avec leur raison (tuilage / cascade — pas des chiffres). `lecteurs_non_declares()` == []. |

### Preuve
- **`pytest tests/` (suite COMPLÈTE) : 0 échec** (les 8 + 3 rouges ci-dessus verts ; ~3099 passed). `verrous -w G8` exit 0.
- Aucun test **retiré** : chaque invariant reste valide, seule la valeur figée avait dérivé (déclaré test par test).
- `tsc -b` : les seuls fichiers non-test touchés sont **backend** (`api/app.py` défaut de fabrication ; `circuit_garanties.py` LECTEURS_ASSUMES) → front inchangé.