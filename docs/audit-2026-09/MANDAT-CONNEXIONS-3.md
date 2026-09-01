# MANDAT CONNEXIONS-3 — Copilote v1 sur la cascade run-scopée

**Branche : `fix/connexions-3`** (depuis `main` après merge de `fix/connexions-2`). Bloc commun habituel.
**Source** : `docs/audit-2026-09/CONNEXIONS-RAPPORT.md`, DOUTE #6 reclassé **KO-LOURD** en Partie B — dernier KO ouvert du rapport.

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter.
**Clôture** : `tsc`, build, tests backend et front, puis **commit sur la branche** avant le compte-rendu. Merge = Vic.

Rappel : on ne supprime aucune table. Toute correction reçoit le test qui aurait attrapé le défaut.

---

## V1 — Le Copilote v1 lit la cascade LIVE non run-scopée

Constat : `copilote/moteurs.py:124-131` et `:343` (4 SELECT) lisent `cascade_results` — la table LIVE marquée obsolète en Partie A. Et **v1 est encore servi** : `CopiloteView` → `/api/copilote/runs` pour les missions lourdes (RECHERCHE, VERIFICATION). Le Copilote peut donc répondre sur des données que la fiche n'affiche plus. C'est le KO le plus visible en démonstration.

1. Les 4 SELECT basculent sur `dryrun_cascade_results`, **run-scopé** par le point de vérité unique livré en Partie A (`Q_A_RUN_LABEL` / `runs.current()`) — jamais un run en dur.
2. Le schéma diffère : établir la correspondance colonne par colonne et la **documenter dans le compte-rendu**. Si un champ lu par v1 n'existe pas dans la table run-scopée, le dire plutôt que d'inventer un équivalent approchant.
3. **Aucun changement du moteur de mission** : v1 garde son comportement, seule sa source change.
4. **Test de non-régression** : une mission RECHERCHE et une mission VERIFICATION renvoient les mêmes parcelles et les mêmes tiers que la fiche écran, sur le run courant ; un leurre seedé sous l'ancien run (`q_v8_calibre`) est ignoré — même forme que `test_served_cascade`.
5. **Recette croisée** : pour 2 parcelles, comparer ce que dit le Copilote (mission lourde) et ce qu'affiche la fiche — tier, zonage, risques, capacité, date de valeur. Identiques.

## V2 — Statut de Copilote v1 : clarifier, ne rien supprimer

L'audit supposait v1 mort, il ne l'est pas. Établir la situation réelle et l'écrire :

1. Quels écrans appellent v1, pour quelles missions, et lesquelles ne sont **pas** couvertes par v2.
2. Ce qui distingue les deux chemins pour l'utilisateur (le voit-il ? deux expériences différentes ?).
3. **Les deux budgets de quota** : v2 et la recherche NL partagent désormais `quota_du_compte` (Partie A, lot 2) ; les missions lourdes v1 gardent un plafond distinct (10 runs/jour, global). Dire si ce plafond est **par compte ou global** — s'il est global, c'est un défaut de cloisonnement à signaler (un compte peut épuiser le quota des autres), avec l'estimation du correctif.
4. Recommandation en 5 lignes : fusionner v1 dans v2, garder les deux, ou retirer v1. Aucune action dans ce mandat — c'est Vic qui tranche.

## V3 — Vérification finale du rapport

1. Reparcourir `CONNEXIONS-RAPPORT.md` et confirmer qu'**aucun KO ne reste ouvert** après V1. Mettre à jour la ligne #6 et la synthèse ; recommiter le rapport.
2. Confirmer qu'aucune lecture de `cascade_results` LIVE ne subsiste **nulle part** (backend, jobs, scripts, CLI) — `grep` exhaustif au compte-rendu. Toute occurrence restante est soit corrigée, soit justifiée par écrit.
3. Lister les tables et endpoints marqués obsolètes depuis CONNEXIONS-2, pour un futur mandat d'hygiène. Ne rien supprimer.

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : V1.2 correspondance de schéma · V1.5 résultat de la recette croisée · V2.3 le plafond des missions lourdes est-il par compte ou global · V3.2 sortie du grep. Commit par CC. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff fix/connexions-3
```
