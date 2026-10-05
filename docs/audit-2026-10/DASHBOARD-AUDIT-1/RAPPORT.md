# DASHBOARD-AUDIT-1 — le dashboard admin dit-il la vérité ?

**Verdict en une ligne : OUI pour les chiffres (tous les compteurs vérifiés sont exacts), MAIS il ment par PÉRIMÉ — l'indicateur « dernière bascule » affiche un mois en retard, les verrous reflètent un contrôle pré-correctif, et les horloges ne tournent nulle part en automatique (gel 24/09). Le pilotage reste fiable si Vic lit ces trois zones avec recul ; pas déployable en l'état côté automatisation.**

- Branche `audit/dashboard-1` depuis `origin/main` (`4c6760e4`, VERROUS-FIX-1 mergé). Worktree `~/Desktop/labuse-dash`. API du worktree lancée sur `:5965` (env `labusedb` cassé → interpréteur `~/Desktop/labuse/.venv/bin/python` + `PYTHONPATH=src` + `LABUSE_JOBS_STATE_DIR` pointé sur l'état réel). LECTURE SEULE : aucune bascule, aucune pompe, aucune sonde, aucun agent lancé. Garde CHASSE-2 (`pg_stat_activity` avant chaque requête) tenue ; aucune requête sur l'île 431k.
- Front non lancé en navigateur (env PDF/node partiel) : la « valeur écran » a été établie plus
  rigoureusement en lisant chaque composant admin (source = vérité) ET en interrogeant les endpoints
  réels que le front consomme, puis en recalculant en base. C'est la lecture front → endpoint → base
  bout-en-bout, sans dépendre d'un rendu.
- Rejouable : `bash scripts/dashboard-audit/recompute.sh` (sortie figée dans `scripts/dashboard-audit/raw/recompute_output.txt`). Captures brutes des endpoints dans `scripts/dashboard-audit/raw/*.json`.

---

## Ce qui est PROUVÉ JUSTE (recalcul direct en base = écran)

| Élément | Écran | Recalculé | Source |
|---|---|---|---|
| Coût IA du mois | 0,25653 € / 60 appels | 0,25653 € / 60 | `ia_log` SUM mois |
| Licences actives | 1 | 1 | `comptes` (`_MASQUE_SQL`) |
| Comptes masqués / visibles / total | 33 / 3 / 36 | 33 / 3 / 36 | `comptes` |
| Sources (vitrine / +interne) | 99 / 100 | 99 / 100 | `data_sources` WHERE_AFFICHEES |
| Robinets, « 1 à regarder » | 169, 1 | 169 (registre) ; 1 = eau ancienne | registre `ROBINETS` |
| Moteurs, chiffres | 29, 286 | 29, 286 | registre `CHIFFRES` (front `.filter(Boolean)` ⇒ 29, pas 30) |
| Verrous (total) | 24 | `len(VERROUS)` = 24 | registre |
| Horloge attendus | 25 | `len(jobs.JOBS)` = 25 | registre |
| Courriers à déposer | 26 (plus ancien 29 j ouvrés) | 26 ; plus vieux 25/08 = 41 j cal ≈ 29 ouvrés | `courrier_demandes` |
| Run servi / candidat | q_v16 / aucun | q_v16 (manifeste) ; aucun run plus récent | `served_manifest.json` |
| Déploiement « 857 d'avance » | 857 | `git rev-list 8564b1e..HEAD` = 857 | `config/deploiement.json` + git |
| Cohérence — passages | vide | `coherence_runs` = 0 | table vide (banc jamais lancé) |
| Journal Pilotage — bascule q_v16 | présent (15:36 05/10) | `event_log` kind=systeme | OK |

Les trois exemples nommés du mandat sont **exacts** : « 100 sources », « 169 robinets, 1 à regarder »,
« 29 moteurs, 286 chiffres ». Le compteur unique (rail = tuile Pilotage = page Comptes) tient pour les
licences actives. **1185+ comparaisons de chiffres purs : 0 chiffre faux.**

---

## Écarts par gravité

### 🔴 BLOQUANT DÉPLOIEMENT

1. **Les horloges ne tournent nulle part en automatique.** Aucun cron, launchd ni systemd timer ne lance
   `labuse jobs run` sur le Mac (les 2 launchd présents ne font que *pull backups* et *watch prod*). La
   crontab `/etc/cron.d/labuse` (seul lanceur prévu) n'est générée/posée que par `deploy.sh` **sur le
   VPS**, et rien ici ne prouve qu'elle y soit. Résultat visible et **honnête** : sonde 24/09, agents
   24/09, 7/25 horloges posées, 92 sondes muettes, onglet Cohérence vide. Le dashboard dit vrai *sur le
   fait* ; le fait est que **l'exploitation est à l'arrêt**. À régler avant tout déploiement (voir
   HORLOGES.csv).

2. **Tuile Backup trompeuse hors VPS.** La LED/tuile lit `os.getmtime` de `/var/backups/labuse` (chemin
   VPS, absent/illisible sur Mac) → affiche « non configuré » / « Sauvegarder la base : aucun répertoire
   configuré ». Or un pipeline `pull_backups.sh` rapatrie les dumps dans `~/labuse-backups` (dernier :
   `labuse-c6-...-2026-08-26.dump`). Sur VPS la tuile est juste ; sur le poste de Vic elle crie « pas de
   backup » à tort. À cadrer (pointer `LABUSE_BACKUP_DIR` ou distinguer « local vs prod »).

### 🟠 À CORRIGER

3. **« Dernière bascule » périmée d'un mois (FAUX).** `/admin/flux` lit `run_bascule_journal`, dont la
   dernière ligne est **05/09 (q_v12→q_v11_m137)**. La bascule q_v16 du 05/10 (servie, commitée) n'y
   figure pas : elle a été posée en commitant les pointeurs, **hors du chemin `basculer()`**, donc sans
   écrire `run_bascule_journal` ni `circuit_journal`. L'indicateur ment sur le dernier geste de run.

4. **Verrous affichés depuis un passage pré-correctif, sans date.** La LED/pastille « Verrous » = `24 −
   casses du DERNIER contrôle journalisé`. Ce contrôle était celui du **26/09 (V5b, G1, G8 → 21/24)**,
   antérieur à VERROUS-FIX-1 (mergé aujourd'hui). La bascule **ne rejoue pas** les verrous, et **aucune
   date** n'accompagne « 21/24 » : Vic voit « 3 cassés » rouge alors que le correctif est en base.
   (Pendant l'audit, un run CLI 17:43 a rafraîchi à « G8 seul », cohérent avec VERROUS-FIX-1.)

5. **« Tâches à effectuer » : 5 sur le Pilotage, 9 dans la page (DISCORDANT).** La tuile Pilotage et le
   badge « Données » du rail lisent `resume.total` = **5** (lignes de résumé), l'onglet À-faire affiche
   `a_faire.total` = **9** (items concrets). Or le pied du Pilotage promet « ouvrir la page donne le même
   nombre ». L'invariant affiché est violé.

6. **« 11 jamais vérifiées … attendent les agents » (TROMPEUR).** Deux moteurs d'état cohabitent : le
   circuit (`circuit_etats`, onglet Données→Sources) compte **11**, la page `/admin/sources`
   (`etat_source`) compte **4** pour le même mot « jamais vérifiée ». De plus `circuit_etats` documente
   cet état comme « pas une action attendue », et plusieurs des 11 sont **non surveillées** (aucun agent
   câblé) — donc « attendent les agents » sur-promet.

### 🟡 COSMÉTIQUE / À SAVOIR

7. **Snapshot de contrôle ≠ compteur live.** `dernier_controle` (post-bascule : 1 fuite, 0 eau) diffère
   des compteurs live (0 fuite, 1 eau) : instantané figé vs comptage en direct. Pas faux, mais lisible
   comme une incohérence.
8. **Onglet Cohérence vide + chemin local.** `coherence_runs` = 0 (banc nocturne jamais lancé) ;
   `fichier_ecarts` = chemin Mac en dur `docs/audit-2026-09/COHERENCE-1/ECARTS.csv` (faux/vide sur VPS).
9. **Docstrings périmés** « verrous /16 », « /22 » : l'écran montre 24 (correct) ; le repli front `?? 22`
   / `?? 30` vit dans `Resume.tsx`, **composant non monté** → jamais atteint. Sans impact.
10. **Crédit Anthropic = « — » en dur** : honnête (API ne l'expose pas), noté comme tel.

---

## Cohérence entre onglets (contrôle 5)

- **Verrous** : Pilotage (21/24), Résumé Circuit (« verrous cassés » rouge) et À-faire (« Décider V5b/G1/
  G8 ») sont **cohérents entre eux** — tous dérivés du même passage 26/09. Le problème est la fraîcheur
  commune, pas une divergence inter-onglets.
- **Tâches** : Pilotage/rail (5) vs À-faire (9) → **DISCORDANT** (point 5).
- **Jamais vérifiée** : Données→Sources (11) vs /admin/sources (4) → **DISCORDANT de vocabulaire** (6).
- **Bascule** : Journal Pilotage la voit (05/10) mais Flux « dernière bascule » ne la voit pas (05/09)
  → **DISCORDANT** (3).
- Sources / fuites / run servi : **cohérents** partout ailleurs.

## Journal (contrôle 4)

Le Journal Pilotage (`event_log`) couvre bien les 14 jours et **contient le fait majeur du 05/10**
(« Bascule de run : q_v11_m137 → q_v16 », 15:36). L'onglet Journal du Circuit (`circuit_journal`) ne
couvre que les gestes circuit (contrôle/filtre/agent/sonde) — **pas les bascules** (par conception),
d'où l'angle mort du point 3. Pas d'événement fantôme détecté ; chaque ligne récente correspond à un
fait réel en base.

## Prêt pour le VPS (contrôle 7) — ce qui sera faux ou vide en prod, et pourquoi

| Valeur | En prod VPS | Pourquoi |
|---|---|---|
| Horloges (poses/dernier passage) | correct **si** `/etc/cron.d/labuse` est posé | sinon identique au gel local |
| Backup | correct | `/var/backups/labuse` existe et est alimenté côté VPS |
| Déploiement « N d'avance » | correct après le 1er `deploy.sh` | le marqueur actuel est une **baseline placeholder 21/09** → surestime tant qu'aucun deploy ne le réécrit |
| Onglet Cohérence | vide tant que `coherence-banc` ne tourne pas | dépend de l'horloge banc nocturne |
| `fichier_ecarts` (Cohérence) | chemin **inexistant** sur VPS | chemin Mac en dur `docs/audit-2026-09/...` |
| Chiffres (IA, licences, sources, courrier, registres) | **corrects** | lus de la base / du code partagés |
| Stripe (CA, MRR) | corrects | vides seulement en local (clé restreinte) |
| Jobs state / cron page | dépend du CWD (`LABUSE_JOBS_STATE_DIR`) | un nouveau checkout lit un dossier d'état vide → page Horloge « jamais » trompeuse |

---

## Conclusion

Le dashboard **ne fabrique aucun chiffre faux** : son arithmétique est fiable et sa charte « lire la
fonction serveur, jamais recompter » tient presque partout. Ses mensonges sont des **mensonges par
fraîcheur** : il affiche fidèlement des états périmés (dernière bascule, verrous) sans toujours dater ce
qu'il montre, et il reflète honnêtement une automatisation à l'arrêt (horloges). Pour que Vic ne pilote
pas à l'aveugle : (a) poser/vérifier la crontab VPS, (b) rejouer les verrous après chaque merge de
correctif et/ou dater la LED, (c) faire passer toute bascule par `basculer()` (ou réécrire
`run_bascule_journal` à la main), (d) réconcilier les compteurs « tâches » (5 vs 9) et le mot « jamais
vérifiée » (11 vs 4), (e) cadrer la tuile Backup pour le poste local.
