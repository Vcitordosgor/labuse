# Dérive de la base de dev vs le run servi `q_v10_m129` — ce qu'une future bascule embarquerait

**But** : documenter les 220 changements de tier qu'un re-score LOCAL produirait vs le run servi
`q_v10_m129` (gelé le **19/08/2026 18:38**), pour qu'à la prochaine bascule on sache ce qu'on
embarque. Mesuré le 22/08/2026. **Aucune bascule faite.**

## Ce qui bouge : 220 parcelles, toutes hors Saint-Philippe

Re-score local aujourd'hui (`rebuild=False`, non servi) vs `q_v10_m129` :

| zone | change | 
|------|-------:|
| Saint-Philippe (97417) | **0** |
| 23 autres communes | **220** |

Transitions (les 220) :

| avant → après | n | sens |
|---------------|--:|------|
| chaude → a_creuser | 124 | sortent de la tête |
| chaude → brulante | 36 | requalifiées dans la tête |
| a_creuser → reserve_fonciere | 51 | entrent en réserve |
| brulante → a_creuser | 7 | sortent de la tête |
| a_creuser → chaude | 2 | entrent en tête |

Dominante : **contraction de la tête** (124+7 = 131 quittent chaude/brulante).

## La cause : recalibrage de la taille de tête, PAS une dérive de données

Fait **certain et vérifié** — le modèle de proba est INCHANGÉ entre les deux runs :
- `taux_base` identique (`0.01553740645543886`), `recale_intercept` = 2025 identique,
  `model_sha256` identique, univers identique (431 663).
- Donc **`p` (proba) et `rang` sont identiques** : aucune parcelle n'a changé de rang. Ce
  n'est PAS une dérive de features/labels (sinon le classement bougerait, pas juste la frontière).

Ce qui change, c'est **le seuil de tête** `n_entree` : **3890 → 2358** (`n_sortie` 5446 → 3301).
`calibre_n_entree` vise ~1 150 parcelles ÉLIGIBLES en tête ; à rang identique, le seuil ne peut
bouger que si la **densité d'éligibles à bas rang** diffère entre le 19/08 et aujourd'hui. La
tête se contracte → 124 chaudes retombent en `a_creuser`, etc.

**Ce n'est pas la PAU CoSIA** : les deux variantes de PAU (2 373 et 2 656) donnent le MÊME
n_entree=2358 (mesuré) ; l'effet PAU sur les tiers est nul (cf. `PAU_COSIA_RESCORE.md`).

## Pourquoi la densité d'éligibles diffère — la piste, et ses limites

L'ensemble éligible dépend de : `plancher_c` (sdp/surface/zone/dans_pau) + les caches
`parcel_constructibilite`, `parcel_au_statut`, `parcel_bati_revele`, `parcel_filtre_bati`,
l'étage 0 (dryrun `q_v10_m129`), copro. **Piste suivie, résultat négatif** :

- **Caches : STABLES**, tous antérieurs au gel de `q_v10_m129` (max computed_at) :
  constructibilité 29/07 · au_statut 09/08 · bati_revele 04/08 · filtre_bati 05/08 ·
  residuel 19/08 **02:30** (avant le run de 18:38). → aucun n'a bougé depuis le run servi.
- **`ingestion_runs` depuis le 19/08 : 1 seule ligne** (BODACC quotidien, 19/08 **01:04**, AVANT
  le run) → aucune ingestion de features postérieure tracée.
- Univers, model_sha, taux : identiques (ci-dessus).

**Conclusion honnête** : l'audit trail tracé (ingestion_runs + horodatage des caches) **ne
contient AUCUNE cause** au recalibrage 3890→2358. La divergence n'est donc pas imputable à une
ingestion ou une correction datée et identifiable côté base.

## L'explication la plus probable : base LOCALE ≠ base du run servi

La doctrine du dépôt (commentaires `fraicheur.py`) est explicite : « le rang servi reste gelé
jusqu'à la prochaine **grande passe (Mac, cf. sync-run.sh)** » ; « la réingestion passe par la
grande passe Mac, jamais un cron ». Autrement dit : **le run servi `q_v10_m129` est produit par
la grande passe (Mac) sur une base maîtrisée** ; la base de dev locale sert au développement et
**diverge** de l'état exact qui a produit le run servi. Un re-score LOCAL lit la base locale →
son `calibre_n_entree` retombe sur un autre seuil (2358) → 220 parcelles à la frontière bougent.

Ce n'est donc pas « telle ingestion du 20/08 a bougé X » : c'est **la base de dev qui n'est pas
la base du run servi**. Le recalibrage est la signature de cet écart (frontière de tête), pas
d'un changement de fond (le classement est intact).

## Ce que ça implique pour la prochaine bascule

1. **Ne jamais basculer depuis un re-score de la base de dev locale** : il embarquerait ces
   ~220 changements d'appartenance à la tête (131 parcelles qui quittent chaude/brûlante, 53 qui
   y (ré)entrent, 51 vers réserve) que **personne n'a décidés** — pur artefact de calibrage
   local, sans changement de rang.
2. **Basculer uniquement depuis une grande passe maîtrisée** (Mac / base regelée), avec un diff
   attendu vs `q_v10_m129` ≈ 0 hors changements explicitement voulus ; tout écart de frontière
   est à expliquer AVANT de servir.
3. La PAU CoSIA améliorée (data-quality, `parcel_pau` 2 656) est neutre sur les tiers
   aujourd'hui : elle s'appliquera sans risque à la prochaine grande passe, sans bascule dédiée.

## Vérif
Mesures faites sur des runs de challenge `rebuild=False`, **non servis, supprimés après**. Run
servi `q_v10_m129` **jamais écrit** ; `parcel_pau` à 2 656 (PAU CoSIA). Aucune bascule.
