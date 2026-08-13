# Runbook — BASCULE DE RUN SERVI (+ règle de rétention M80)

> La bascule de run change ce que TOUT le monde voit. Elle est atomique et suivie d'une purge de
> rétention. (À ne pas confondre avec `BASCULE_LIVE_CHECKLIST.md` = bascule Stripe/paiement.)

## Procédure de bascule (ordre strict)

1. **Générer le nouveau run** (`labuse dryrun-evaluate --label <nouveau>` sur le périmètre voulu),
   vérifier son intégrité (funnel, golden en dry-run).
2. **Faire suivre les DEUX pointeurs versionnés ENSEMBLE** :
   - `config/run_precedent.txt` ← l'ancien servi (l'actuel `config/served_run.txt`) ;
   - `config/served_run.txt` ← le nouveau run.
   (Les deux sont le point de vérité unique ; jamais un nom de run codé en dur ailleurs — M80.)
3. **Rebâtir les surfaces** : `npm run build` (bundle → VITE_RUN_LABEL) + `labuse build-mvt`
   (tuiles → `mvt_meta.run_label`). Vérifier `tests/test_run_serving_coherence.py`.
4. **Rebâtir les dérivés du geste** qui comparent deux runs (ex. `lignee_tete.build_parcel_entree_tete`
   si la lignée change).
5. **RÉTENTION — purge des runs devenus obsolètes** (voir ci-dessous).

## Règle de rétention (M80)

**On garde : le SERVI + le PRÉCÉDENT + tout run encore RÉFÉRENCÉ** (lignée `lignee_tete`, exceptions
`served_run_exceptions`, démo `q_v2_demo`). **On purge le reste.**

- Pourquoi « servi + précédent » : le précédent permet de mesurer le diff d'une bascule (accueil
  `bascules_tiers_hauts`). Au-delà, un run n'apporte plus rien qu'un dérivé matérialisé ne porte déjà.
- **Un run référencé n'est JAMAIS purgé** (règle Vic). La commande calcule l'ensemble « à garder » à
  partir des points de vérité + des références réelles en base ; elle ne devine rien.
- **Cycle de vie ATOMIQUE** (défaut #1, RAPPORT_M80) : un run se crée ET se purge dans TOUTES les
  tables run-scoped ensemble — jamais « à moitié ». La commande balaie toutes les colonnes
  `run_id`/`run_label` de type texte et supprime le run partout d'un coup.
- **Déclenchée À LA BASCULE**, jamais par un cron indépendant (une purge qui tourne seule, sans le
  geste qui la justifie, finit par surprendre).

### Commande
```
# 1) dry-run (rien supprimé) — LIRE la liste « à purger » et « à garder »
labuse purge-runs-morts

# 2) exécuter — APP ARRÊTÉE (VACUUM FULL prend un verrou exclusif)
sudo systemctl stop labuse       # ou couper l'uvicorn local
labuse purge-runs-morts --apply  # DELETE atomique sur toutes les tables run-scoped + VACUUM FULL
sudo systemctl start labuse
```

### Garde-fous
- **Jamais le run servi** (il est dans l'ensemble « à garder » par construction).
- **Jamais un run référencé** (idem).
- **App arrêtée** avant `--apply` (VACUUM FULL).
- Après : `labuse purge-runs-morts` (dry-run) doit afficher « Aucun run à purger », l'app démarre,
  fiche + exports 200, `golden_check.py` inchangé.
- **VACUUM FULL a besoin d'espace** (réécrit chaque table purgée) : si une table échoue faute de
  place → STOP, ne pas tenter la suivante (mesurer, libérer, reprendre).
