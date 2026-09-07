# Lot B — Le batch `blocs-build`

## La commande (à lancer par Vic — NON exécutée automatiquement)

```bash
export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse"
export PYTHONPATH="$PWD/src"      # worktree feat/blocs-fonciers
labuse blocs-build               # ou : python -m labuse.cli blocs-build
```

Doctrine d'injection sur **clic humain** : le batch ne tourne jamais seul (aucun cron, aucun
appel depuis un run). CC l'a écrit, testé et documenté ; c'est Vic qui le lance.

## Ce qu'il produit

Deux tables (créées si absentes, `ensure_schema`, idempotent) :

- **`parcel_blocs`** — un enregistrement par bloc : `bloc_key` (déterministe `siren:min(idu)`),
  `siren`, `denomination`, `n_parcelles`, `surface_totale_m2`, `communes[]`, `sdp_residuelle_m2`
  (somme, **Estimé**), `sdp_couverture` (nb de parcelles ayant un résiduel connu), `zonages[]`,
  `residuel_run_seq` (run résiduel servi épinglé), `built_at`.
- **`parcel_bloc_membres`** — une ligne par parcelle du bloc : `idu`, `parcel_id`, `surface_m2`,
  `commune`, `zone`, `sdp_residuelle_m2` (de cette parcelle).

## Règles de regroupement (B3), explicites

| Règle | Valeur | Source |
|---|---|---|
| Contiguïté | `ST_DWithin(geom_2975, 0,5 m)` | `assemblage.ADJ_BUFFER_M` (constante unique) |
| Propriétaire | **même SIREN** | `parcelle_personne_morale.siren` |
| Périmètre | **personnes morales seulement** | particuliers sans identité stable → exclus |
| Cadastral | couche `parcels` (IDU 14 car.) | domaine public non cadastré absent → règle satisfaite par construction |
| Taille | **≥ 2 parcelles** | `blocs.MIN_PARCELLES` |
| Résiduel | somme des résiduels, vue servie `parcel_residuel` | statut **Estimé** |

**Règles ajoutées par CC (signalées) :** aucune règle métier neuve. Un seul choix technique —
`bloc_key = siren:min(idu)` comme clé déterministe pour l'idempotence — et le résiduel se lit sur
la **vue servie `parcel_residuel`** (le pin scoring `q_v11_m137` ne porte pas le résiduel ;
cohérent avec « aucun badge de score »). Aucun filtre de surface (pas d'exclusion de slivers) :
toutes les parcelles cadastrales du SIREN comptent, conformément au mandat.

## Rejouable & idempotent

`DELETE FROM parcel_bloc_membres; DELETE FROM parcel_blocs;` puis rebuild, dans **une seule
transaction** (commit par la commande). Journalisé comme un run (`run_progress.start/progress/
finish/abandon`, état `/tmp/labuse-blocs-build.json`). Rejouer produit un contenu **identique**
(clé déterministe) — prouvé : deux runs consécutifs, même checksum `md5(bloc_key)` =
`55a8d0de5ac2314090798595f85d7f5b`.

## Mesure réelle (base `labuse`, île entière)

- **11 225 blocs**, **59 835 parcelles** regroupées — identique au cadrage Lot A.
- Durée **~25 s** (contiguïté 18 s + agrégation/écriture).
- Résiduel servi `run_seq=2` (m135-run2-ile) ; SDP résiduelle agrégée totale ≈ 24,3 M m².

## Tests (`tests/test_blocs.py`, PostGIS réel)

1. **Bloc connu vérifié à la main** — 2 parcelles contiguës même SIREN → 1 bloc, IDU/surface
   (1 240 m²)/résiduel (450 m²)/zonages (UA,UB)/`bloc_key` vérifiés.
2. Parcelle **isolée** (SIREN à 1 parcelle) → aucun bloc.
3. Deux parcelles contiguës de **SIREN différents** → non regroupées.
4. Deux parcelles contiguës **sans PM** (particulier) → hors périmètre.
5. Même SIREN mais parcelles **éloignées** → non regroupées.
6. **Idempotence** — deux builds, même contenu.
