# RESIDUEL-1 — un seul chemin de calcul du résiduel, la zone rouge découpée partout

*Branche `fix/residuel-1` (worktree `~/Desktop/labuse-residuel`, base locale q_v20, prod LUE EN LECTURE
SEULE, zéro écriture). Base de départ `c959d351e`. Non mergée.*

## 0. Le défaut (rappel — DOCS-1 §11-13)

Deux chemins calculaient le même résiduel, et donnaient deux verdicts :

| Chemin | Appel | Branche | Zone rouge PPR |
|---|---|---|---|
| **Run de nuit** (`compute_residuel_batch`) | `parcel_faisabilite(assiette_clippee=False)` | héritée (`db.py`) | **non découpée** → toute parcelle touchée fermée « rédhibitoire », SDP 0 |
| **Fiche en ligne** (`fiche_payload`) | `parcel_faisabilite(assiette_clippee=True)` | gabarit (PPR-PARTIEL-A) | **découpée** → constructible sur la partie hors rouge |

Conséquence servie : ~216 parcelles en zone U, partiellement rouges, classées à **score 0 / bande 0**
(`residuel_socle −25`) et **exclues du tri « À construire »**, alors que leur fiche les disait
constructibles. DOCS-1 réconciliait à la LECTURE (`verdict_ppr_partiel`) ; RESIDUEL-1 répare la SOURCE.

## A. Le code — un seul chemin, clippé par construction

Le flag `assiette_clippee` a **disparu** de tout le moteur résiduel. Il n'a plus de contraire : le run
de nuit, la fiche, le bilan, les scénarios, les tuiles, le tri « À construire » et le socle
`residuel_socle` lisent désormais le **même** `compute_residuel` → **même verdict, même SDP, même
emprise**.

| Fichier | Changement |
|---|---|
| `faisabilite/db.py` | `parcel_faisabilite(…)` perd le paramètre ; l'assiette gabarit, la découpe des contraintes certaines (**PPR rouge compris**) et le clip de surface à la portion U/AU sont **inconditionnels**. La branche legacy (`gab is None`) subsiste comme SEUL repli quand le moteur gabarit ne sert pas la parcelle (gabarit bloquant / zone non constructible) — elle découpe elle aussi le rouge désormais ; ce n'est plus la « branche héritée » qui fermait toute parcelle rouge. |
| `faisabilite/residuel.py` | `compute_residuel` / `compute_residuel_batch` perdent le paramètre ; le clip de bâti sur la portion U/AU est inconditionnel. |
| `api/app.py`, `faisabilite/scenarios.py`, `scripts/donnees_fix1_golden.py` | appels mis au chemin unique. |
| `cli.py` | `compute-residuel` perd le flag `--assiette-clippee` (clippé par construction). |
| `scripts/residuel_shard.sh` | n'envoie plus `--assiette-clippee`. |

**La réconciliation DOCS-1 reste en garde-fou, mais ne change plus un verdict frais.**
`verdict_ppr_partiel` / `_override_ppr_partiel` ne se déclenchent QUE lorsque le run stocké FERME la
parcelle (`cause` présente). Dès que le run est recalculé en assiette clippée, la cause de ces
parcelles devient NULL → `potentiel_batir` sert le run tel quel et **n'appelle jamais** l'override. Le
filet reste disponible tant qu'un run périmé est servi ; il s'efface de lui-même une fois le run frais.

**Tests** (`tests/test_residuel1_chemin_unique.py` + mises à jour) :

- `test_aucune_variante_non_clippee_ne_subsiste` — verrou de structure : aucun `assiette_clippee` ne
  réapparaît (moteur + CLI).
- `test_batch_egale_fiche_sur_les_temoins` (`reel`) — sur **DH0076, AK0804, BZ1065, AB0133**, le calcul
  « batch » (résout la faisabilité) et le calcul « fiche » (reçoit la faisabilité) rendent EXACTEMENT
  le même `(disponible, cause, SDP résiduelle, SDP écrite, emprise)`. Vérifié sur la base réelle.
- `test_dh0076_constructible_hors_rouge_au_run` (`reel`) — DH0076 (U, 2 % rouge) : cause NULL, SDP > 0.
- `test_reconciliation_ppr_partiel_no_op_sur_run_frais` — run frais (cause NULL) : pas d'override,
  `verdict_ppr_partiel` jamais appelé.
- `test_reconciliation_ppr_partiel_arme_quand_run_perime` — symétrie : run périmé → le filet opère.

Hook unitaire vert ; familles faisabilité/scoring/potentiel/scénarios vertes (274 passed sur le sous-
ensemble ciblé).

## B. Simulation PROD (lecture seule) sur les 448 parcelles `cause='redhibitoire'`

Rejouée en LECTURE SEULE le 2026-11-08 (`ssh labuse-vps`, transaction forcée `READ ONLY`, run servi
**17 = q_v20**, univers **433 229**). Le nouveau chemin unique y est reproduit sur le code en place en
appelant `compute_residuel(pid, assiette_clippee=True)` — identique, parcelle par parcelle, à
`compute_residuel(pid)` du code `fix/residuel-1` (égalité vérifiée sur les 4 témoins). **Aucune
écriture.** Script : `scripts/residuel1_prod_sim.py`. Détail : `reports/residuel-1/flips_redhibitoire.csv`
(448 lignes : IDU, commune, zone, part rouge %, SDP avant, SDP après, verdict) + `prod_sim_raw.txt`.

### Combien changent de verdict

| Issue | n | Détail |
|---|---:|---|
| **Flip → CONSTRUCTIBLE** (cause NULL) | **339** | dont **190 avec SDP > 0** → **ré-entrent dans le tri « À construire »** (≈ **748 597 m²** de SDP recouvrée, moyenne ~3 939 m²) ; 149 constructibles mais SDP 0 (saturées — « déjà bâties au maximum » : plus « rédhibitoire » à tort, mais rien à construire) |
| **Restent fermées** (légitime) | **109** | 100 toujours `redhibitoire` (facteur de modulation nul même rouge découpé — vraiment inconstructibles) ; 9 `terrain_exigu` (fragment hors rouge < 200 m² / sans accès) |
| **Erreurs** | 0 | |

Sur les 448, **215 touchent réellement une zone rouge PPR** (≈ les 216 du constat DOCS-1) ; les 233
autres étaient « rédhibitoire » pour une **modulation périmée** sans lien avec le rouge, que le chemin
clippé corrige aussi. Les 109 qui restent fermées le sont à bon droit (dont 45 sans aucun rouge,
inconstructibles par le moteur ; 55 fortement rouges). **Témoin DH0076** : `U2b`, 2,4 % rouge, SDP
**0 → 26 258**, CONSTRUCTIBLE — conforme à la fiche (26 258).

### Temps estimé d'un recalcul de l'île entière (nouveau chemin)

- **Débit mesuré sur l'échantillon rédhibitoire : 3,7 parcelles/s.** C'est la BORNE HAUTE du coût : les
  parcelles rédhibitoires sont précisément celles qui déroulent tout le moteur gabarit + la géométrie
  PPR (le chemin le plus cher). L'extrapolation naïve 433 229 / 3,7 ≈ **32 h** est donc trompeuse.
- **Ancrage réel** = durées des runs résiduels île DÉJÀ clippés (même moteur) : q_v20 **5 h 17**
  (19 057 s), q_v18 **5 h 24** (19 416 s), q_v16 **7 h 13** (25 984 s). La moyenne du parc (beaucoup de
  parcelles non constructibles / mono-zone qui court-circuitent) tire le débit bien au-dessus de 3,7/s.
- **Attendu : ~5–7 h en process unique** ; **~2–3 h avec 2–4 shards** de communes disjointes
  (`scripts/residuel_shard.sh`, mesuré ~50 p/s à 2 shards) — **si la mémoire tient** (ne pas
  sur-sharder quand la machine swappe : le calcul est DB-bound).

## C. Procédure de recalcul en prod (prochain déploiement)

> Doctrine : **le run servi n'est jamais remplacé « à vif ».** Un run neuf est calculé dans un
> `run_seq` NEUF (les runs coexistent par clé `run_seq, parcel_id` ; `assert_writable` refuse
> d'écrire dans le servi), puis servi par un **flip atomique réversible** (`is_served`) — c'est la
> garde `garde_injection` / `injection_sure` (staging + swap atomique + retour arrière) appliquée aux
> runs. Toute l'opération se fait **hors fenêtre de calcul de nuit 01:00–05:00** (heure Réunion) pour
> ne pas entrer en collision avec `calcul-nuit` (`_fenetre_calcul_ok`).

### 1. Déployer le code (staging → swap atomique)

```sh
# depuis le poste local, worktree fix/residuel-1 mergé dans la branche de déploiement
bash deploy/scripts/deploy_app.sh        # rsync DIRECT → /opt/labuse/app ; EXCLUT /reports et
                                         # config/served_* (l'état servi appartient à la prod) ;
                                         # recharge labuse.service
ssh labuse-vps 'labuse rebuild --dry-run'  # fumée fraîcheur : échoue si un cache dérivé est périmé
```
- **Hors 01:00–05:00.** Le swap de code est un `rsync --delete` + reload du service (atomique côté
  systemd) ; aucune table servie n'est touchée.
- **Surveillance** pendant et après : `systemctl status labuse`, `/readyz` (doit rester `true`),
  `NRestarts=0`, `journalctl -u labuse` sans trace. Le code seul ne recalcule RIEN : le run servi
  (q_v20) continue d'être lu jusqu'au swap de run (étape 4).

### 2. Calculer le run résiduel neuf (le chemin unique)

```sh
ssh labuse-vps
caffeinate_or_nohup labuse compute-residuel --ile --new-run "q_vNN residuel-1 (chemin unique clippé)"
# ou, pour aller plus vite si la mémoire tient (2 shards de communes DISJOINTES dans UN run) :
#   labuse compute-residuel --ile --new-run "q_vNN residuel-1" --chunk 1   # crée le run_seq, 0 parcelle
#   RS=<run_seq relevé via `labuse residuel-runs`>
#   psql "$LABUSE_DATABASE_URL" -tAc "SELECT DISTINCT commune FROM parcels ORDER BY commune" > /tmp/communes.txt
#   awk 'NR%2==1' /tmp/communes.txt > /tmp/shardA.txt ; awk 'NR%2==0' /tmp/communes.txt > /tmp/shardB.txt
#   caffeinate -i scripts/residuel_shard.sh $RS /tmp/shardA.txt &
#   caffeinate -i scripts/residuel_shard.sh $RS /tmp/shardB.txt &
```
- **Budget ~5–7 h mono / ~2–3 h à 2–4 shards** (cf. §B). DB-bound.
- **Surveillance mémoire & disque** (obligatoire — le moteur gabarit est lourd) :
  - `free -m` / `vmstat 5` : si `swap` se met à travailler, **réduire le nombre de shards** (le débit
    s'effondre bien avant l'OOM). Pas de sur-shard.
  - `df -h` sur le volume Postgres : un run neuf ≈ taille d'un run (× 433 k lignes `parcel_residuel_runs`)
    + les temporaires PostGIS. Vérifier **avant** de lancer qu'il reste la marge d'un run.
  - Le run écrit dans `parcel_residuel_runs` (NON servi) : zéro impact sur le service pendant le calcul.
- Le run neuf coexiste avec q_v20 ; `assert_writable` garantit qu'on n'écrit jamais dans le servi.

### 3. Contrôles de promotion (avant de servir)

Comparer le run neuf au servi — les écarts ATTENDUS ne sont pas des régressions :

```sh
labuse residuel-runs                     # relever run_seq neuf + servi
```
- **Flips attendus** : ~339 parcelles `redhibitoire → constructible` (dont ~190 à SDP > 0 ré-entrant au
  tri « À construire »). C'est l'OBJET du mandat — à retrouver, pas à craindre. Rejouer la simulation
  §B sur le run neuf (comparer `parcel_residuel_runs` neuf vs q_v20 `cause='redhibitoire'`) : le compte
  doit tomber sur l'ordre de 339/109.
- **Cohérence fiche ↔ run = 0 écart** : sur un échantillon (au moins DH0076, AK0804, BZ1065 + N
  témoins), `compute_residuel(pid)` live doit égaler la valeur stockée au run neuf (c'est désormais le
  même chemin — l'écart doit être nul).
- **Comptes** : univers couvert du run neuf = univers vivant servi (433 229), 0 trou, 0 doublon
  (clé `run_seq, parcel_id`).
- **Paliers / classement** : le résiduel alimente `residuel_socle` → le Score. Après bascule (étape 4),
  rejouer `labuse recompute-paliers <scoring_run> <cascade_run>` pour que les ~190 parcelles à SDP > 0
  réintègrent les bandes et le tri « À construire » (sans quoi le run neuf sert la bonne SDP mais le
  classement reste sur l'ancien socle).
- **Banc de cohérence** (`03:45`, hors charge) : doit rester **0/0** une fois le run frais servi.

### 4. Servir — flip atomique, réversible

```sh
labuse residuel-serve <run_seq_neuf>     # bascule is_served (atomique) + réaligne le manifeste
                                         # miroir + lance `labuse rebuild` détaché (tuiles, fiches)
# retour arrière immédiat si besoin :  labuse residuel-serve <run_seq_q_v20>
```
- **Hors 01:00–05:00.** Le flip est un `UPDATE residuel_runs SET is_served` dans une transaction
  (contrainte d'unicité `WHERE is_served`) — instantané et **réversible** (rappeler l'ancien seq).
- `residuel-serve` **réaligne le manifeste** (`residuel_run_seq`) — **à commiter** (il l'affiche) — et
  relance `labuse rebuild` (caches dérivés : tuiles `mvt_parcels`, `fiche_cache`…), sinon la carte
  contredirait la fiche.
- Surveiller `/tmp/labuse-rebuild-residuel-seq<NN>.log`, puis `labuse rebuild --dry-run` (fumée).

### 5. Promotion

`LABUSE_CALCUL_NUIT_PROMEUT=0` reste la règle : **Claude ne promeut pas.** Une fois les contrôles §3
verts et la bascule §4 faite, la promotion (et l'arbitrage des écarts de comptes s'il en reste) revient
à **Vic** (via John). Si un contrôle échoue, le run neuf est **archivé** (non servi, il reste en base) et
ne bloque pas la nuit suivante (`candidat_nuit`) ; on sert à nouveau q_v20 (étape 4, retour arrière).

---

*RESIDUEL-1 — prod jamais écrite. Simulation : `scripts/residuel1_prod_sim.py` (lecture seule) ;
détail `reports/residuel-1/`. Tests : `tests/test_residuel1_chemin_unique.py`. Branche `fix/residuel-1`,
non mergée.*
