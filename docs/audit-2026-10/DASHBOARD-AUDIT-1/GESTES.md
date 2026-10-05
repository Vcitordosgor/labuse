# GESTES — ce que fait chaque bouton du dashboard, et le geste à faire après

Audit LECTURE SEULE (aucun clic) : lecture du front (`frontend/src/components/admin/`) et du back
(`dashboard.py`, `ops.py`, `bascule_flux.py`, `golden_ops.py`, `manifeste.py`, `filtres/`).

**Fait transverse capital.** Les trois pointeurs `config/served_run.txt`, `config/run_precedent.txt`,
`config/served_manifest.json` sont **suivis par git**, et **aucun geste du back n'appelle git**
(`grep` de `git commit|git add|subprocess.*git` sur tous les modules de geste = 0). Donc tout geste qui
écrit un de ces fichiers **salit l'arbre de travail** : c'est exactement le précédent q_v16.

## Les deux seuls gestes qui salissent l'arbre

### Basculer sur \<candidat\> (Circuit → Pompe)
- Front `postAdminFluxBascule` → **POST /admin/flux/bascule** → `bascule_flux.basculer()`.
- Écrit : **`config/served_run.txt`** (`golden_ops.promote`), **`config/run_precedent.txt`**,
  **`config/served_manifest.json`** (écriture atomique) ; DB `run_bascule_journal` +
  `circuit_journal` + `DELETE zone_isochrone_cache` + notification ; purge caches process ;
  **subprocess détaché `labuse rebuild`** si le plan tuiles tient en < 15 min. **Pas de git.**
- **Laisse l'arbre sale ? OUI** — les 3 fichiers `config/*`.
- **Geste après** : **commit des 3 fichiers** (BASCULE_RUN_RUNBOOK §2 ; `smoke_test.sh §7` BLOQUE au
  déploiement si le manifeste commité ≠ `residuel_runs.is_served`) + `npm run build` (VITE_RUN_LABEL)
  + `labuse purge-runs-morts` (app arrêtée) + **`deploy/scripts/sync-run.sh`** (pousse le run au VPS).

### Revenir à \<précédent\> (Circuit → Pompe)
- Front `postAdminCircuitRevenir` → **POST /admin/circuit/revenir** → `basculer(sens="arriere")`.
- **Identique à Basculer** (réécrit les 3 mêmes fichiers, restaure le manifeste précédent).
- **Laisse l'arbre sale ? OUI.** **Geste après** : identique (commit + rebuild + déploiement).

## Tous les autres gestes — NE touchent AUCUN fichier versionné

| Bouton | Endpoint | Écrit | Arbre sale ? | Geste après |
|---|---|---|---|---|
| Calculer / Faire tourner la pompe | POST /admin/flux/run/lancer | subprocess `flux-run` → DB (run candidat), log /tmp | NON | rien (candidat ; lire la Note puis Basculer) |
| Arrêter le run | POST /admin/flux/run/arreter | SIGTERM + état /tmp | NON | rien |
| Injecter / Recharger une source | POST /admin/sources/{id}/veille/injecter · /relancer | subprocess ingestion → DB + source_veille | NON | suivre ingestion ; si à servir → Calculer+Basculer |
| Envoyer un/les agent(s) | POST /admin/circuit/agents | thread agent LLM → DB + coût ledger | NON | rien (résultat au Journal) |
| Servir quand même | POST /admin/circuit/filtre/servir-quand-meme | UPDATE filtre_versions | NON | rien |
| Revenir à la précédente (filtre) | POST /admin/circuit/filtre/revenir | **DDL** DROP/RENAME tables servies (destructif) | NON | rien |
| Suspendre/Reprendre veille | POST /admin/sources/{id}/veille/active | UPDATE source_veille | NON | rien |
| Dégeler | POST /admin/degeler | UPDATE acces_gels | NON | rien |
| Lancer maintenant (Horloge) | POST /admin/cron/{nom}/run | subprocess `labuse jobs run` + logs/verrou | NON* | rien (*sauf si le job touche des données servies) |
| Purger les runs morts | POST /admin/circuit/purger-runs | DRY-RUN (journal) seulement | NON | exécuter la CLI `--apply` hors serveur |
| Sonder / Relancer verrous | POST /admin/circuit/sonder · /verrous | tâches de contrôle → DB | NON | rien |
| Licences (Créer/Essai/Convertir/Prolonger/Suspendre/Rétablir/Déconnecter/Quota/Mail) | /admin/licences/... | DB comptes/quotas + mail_queue | NON | rien |

## Garde-fous existants (déjà au code)
- `bascule_flux.avertissement_arbre()` prévient si la bascule tourne depuis un worktree ≠ arbre
  d'installation éditable (le manifeste serait écrit dans le mauvais checkout).
- La bascule relit `runs.current()` après écriture et refuse de confirmer si la valeur relue ≠ demandée
  — **mais ne commite jamais** : l'arbre reste sale quoi qu'il arrive.
- `deploy/scripts/smoke_test.sh §7` (BLOQUANT) : rattrape un manifeste non commité/périmé au déploiement.

## Observé pendant l'audit (à savoir)
La bascule q_v16 servie le 05/10 **a bien été commitée** (`777e44d0 bascule: scoring servi q_v16`,
`962946d4 serve: résiduel run 13`) — l'arbre est propre. **Mais** elle n'a **pas** écrit
`run_bascule_journal` ni `circuit_journal` (dernière bascule journalisée = 05/09) : elle a été posée en
éditant/commitant les pointeurs, hors du chemin `basculer()`. Conséquence dashboard : l'indicateur
« dernière bascule » de /admin/flux affiche le 05/09 (voir RAPPORT, écart FAUX).
