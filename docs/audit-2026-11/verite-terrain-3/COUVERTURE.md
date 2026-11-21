# VERITE-TERRAIN-3 — COUVERTURE : ce qui a été testé, ce qui ne l'a pas été, et pourquoi

Audit du 15/11/2026, lecture seule. Moteur testé = **main `e269abaa0`** (HEAD de `origin/main`,
identique à la base de la branche d'audit). Classement servi = run **q_v20** (`served_manifest.json`,
`residuel_run_seq` 17, promu le 21/10/2026). Base locale `labuse` (PostgreSQL 18.4, 295 tables).

## Testé

| Volet | Donnée | Effectif |
|---|---|---|
| Rejeu VT-2 (volet D d'octobre) | mêmes 6 601 permis PC/DP post-PLU, moteur du jour, run servi 17 | 6 601 permis, transitions par cas |
| Test 1 — verdict | cohorte H (PC logements, dédoublonnés, parcelles existantes, post-règles) | 4 812 permis |
| Test 1 — relecture des « non » | tirage à graine fixe `VT3-LOT2-60` parmi 180 | 60 permis |
| Test 2 — enveloppe | H mono-parcelle, enveloppe mesurable | 4 096 permis |
| Test 2 — relecture dépassements | les 40 ratios autorisé/enveloppe les plus forts (>1,10) | 40 permis |
| Test 3 — classement | R (426 parcelles à permis récent, terrain nu) vs T (1 272 tirages comparables) | 1 698 lignes |
| Test 3 — relecture | tirage `VT3-LOT4-30` parmi les 92 R classées Faible/Non retenue | 30 parcelles |
| Signal secondaire | ventes DVF « terrains a bâtir » 2021-2025 sans local bâti | 4 230 ventes, relecture 20 (`VT3-LOT5-20`) |
| Défauts VT-2 | 418 « non constructible » et 913 « densité » d'octobre, transition cas par cas + relecture 21 régressions + 20 restants | — |

## Pas testé, et pourquoi

- **LOT 6 (précision des prix)** : écarté sur instruction — le banc sans fuite a été fait par
  VERITE-TERRAIN-2 volet E (3 581 ventes, −5,6 % médian signé, ±10 % = 17,5 %) et DVF s'arrête
  toujours au 31/12/2025 : le rejouer aujourd'hui redonnerait les mêmes chiffres sur les mêmes
  ventes. Référence : `docs/audit-2026-10/verite-terrain-2/PRIX-BACKTEST-NOTES.md`.
- **Niveaux / hauteur autorisés des permis** (Test 2, volet « compare-les au maximum de LABUSE ») :
  la donnée N'EXISTE PAS dans `sitadel_permits` (clés `raw` exhaustives relevées : etat, famille,
  nb_lgt, surf_hab, destination, daact, insee, adr_*, geoloc, parcelles_actuelles,
  origine_redecoupee, parcelle_origine, petitioner_*, src, pv, date_*_brute). Aucun champ inventé.
- **Typologie Sit@del individuel / collectif / résidence** : pas davantage dans la donnée ingérée
  (pas de NB_LGT_IND/COL/RES). Approximation assumée par `nb_lgt` (1 = individuel, ≥2 =
  collectif/groupé) ; « résidence » indistinguable.
- **Surfaces démolies / conservées** : absentes de la donnée (seule `surf_hab` créée existe). Le
  Test 2 compare donc le CRÉÉ autorisé à l'enveloppe « terrain libéré » — cohérent, mais un permis
  de démolition-reconstruction n'est pas distingué d'une construction sur terrain nu.
- **« Image de la page du règlement »** : les PDF des règlements ne sont pas sur ce poste et
  l'audit est hors réseau. La preuve servie est le **verbatim** de `plu_reglement_extrait`
  (3 258 extraits, 21 communes, article + page + URL source) — même source que les volets A de
  VT-1/VT-2. Saint-André (97409) et Saint-Leu (97413) n'ont pas d'extraits en table : les cas de
  ces communes citent le YAML calibré et le disent.
- **Saint-Philippe (97417)** : au RNU, pas de date de « règles actuelles » ; ses 245 permis
  (après les autres filtres) sont exclus de H et décrits dans l'entonnoir.
- **Fiches illustrées** : la « fiche LABUSE » des 30 cas de `~/Desktop/verite-3/` est une fiche
  textuelle reconstruite (verdict moteur, étapes du calcul, classement servi, ligne du permis) —
  pas une capture d'écran de l'application (serveurs non lancés pour garder l'audit hors service).

## Limites de méthode (assumées, héritées de VT-2 quand identiques)

- `surf_hab` Sit@del est une surface HABITABLE ; conversion plancher ×1,15 (COEF_PLANCHER) avant
  tout ratio — approximation dite.
- La date de « règles actuelles » = millésime du règlement MODÉLISÉ par LABUSE
  (`config/plu_destinations/*.yaml`), croisée avec Sudocuh (`approbation_opp`) et le GPU
  (`idurba`) dans le LOT 0 du RAPPORT. Un permis instruit sous l'ancien règlement mais autorisé
  juste après le millésime peut subsister dans H (classé « décalage » en relecture, jamais
  « erreur »).
- L'état « jamais commencé » (cohorte R) vient d'`etat=2` Sit@del, croisé avec le bâti LABUSE
  (`p_model_bati` < 20 m²) — double verrou, mais Sit@del peut être en retard sur le chantier réel.
- Doublons : 599 doublons exacts et 3 660 resoumissions même assiette retirés (le plus récent
  gardé) ; les « modificatifs » à suffixe M (131) n'ont pas de permis de base en table (mesuré) et
  comptent comme des permis à part entière.

## Annexe — qui lit les permis dans LABUSE (et pourquoi les tests ne sont pas circulaires)

`grep sitadel_permits` touche 56 fichiers ; ceux qui comptent pour l'audit :

| Lecteur | Usage | Entre dans verdict / bandes / SDP ? |
|---|---|---|
| `zone.py:710` (`_permis_par_zone`) | compteur d'autorisations de la fiche zone | Non — affichage |
| `signaux_vie.py:90` | signal « permis actif < 3 ans » (widget veille) | Non |
| `cascade/layers/phase2.py:87` (couche `sitadel`) | BONUS `permis_sitadel_recent_proximite` dans la cascade du Signal | Non — bonus du Signal de mutation ; les exclusions dures (bande HC) viennent d'autres couches (route, DPF…) |
| `scoring/p_v2/qv14.py:207`, `p_model/sql.py`, `regles/n_permis_proximite.py` etc. | features du **Signal de mutation** (probabilité de vente) | Non — le Score LABUSE (bandes Excellente…Non retenue) = capacité × faisabilité, sans Signal |
| `faisabilite/viabilisation_build.py` | contexte de coût de viabilisation (bilan) | Non — coût, pas capacité |
| `verite_terrain*.py` | modules d'audit (VT-1/2/3) | hors service |
| `ingestion/*` (pc_caducs, filiation, dfi…) | ingestion et veille | Non |

Le verdict (`faisabilite/engine.py` + `potentiel_batir.py`), le Score et ses bandes
(`scoring/score_labuse.py` : `parcel_residuel`, terrain, LiDAR, AU, cascade `acces`) et la
surface à retenir (`faisabilite/surface_retenue.py`) ne lisent jamais `sitadel_permits` :
les tests 1-3 confrontent bien LABUSE à une vérité qui ne l'alimente pas.
