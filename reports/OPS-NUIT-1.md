# OPS-NUIT-1 — nuit du 2→3/11 : sauvegardes, calcul de nuit, résumé du matin, mails

Lancé le **2026-11-03** (après-midi, Réunion +04) depuis `~/Desktop/labuse-main`, prod `labuse-vps`
(`https://app.labuse.immo`). Go de Vic, accès prod limité au mandat (lecture + les gestes décrits).
Branche **`fix/ops-nuit-1`** (poussée), déploiement court selon `reports/DEPLOY-AUTONOMIE-2.md`.
Prod avancée de **`c7772aae9`** → **`38c74a643`** (q_v20 toujours servi, aucune bascule).

> **Bilan en une ligne.** Les bonnes sauvegardes sont protégées (hardlinks `GARDE-`, 0 octet) ; le
> « dump de 1,2 Mo » **n'existe pas** — celui du jour est bon (6,2 Go, 294 tables) — mais la vraie
> faille (un dump rétréci peut évincer un bon en rotation) est fermée par une **garde anti-rétrécissement** ;
> l'échec du **calcul de nuit à 02:59 Paris** vient d'une **transaction laissée ouverte pendant les
> ~4 h de calcul** (tuée par `idle_in_transaction_session_timeout`), corrigé **à la source** + fenêtre
> **reprenable** ; le **résumé du matin** n'était **pas câblé** → nouveau job quotidien qui part **tous
> les jours** ; mails refondus (**[URGENT]/[INFO]**, lien d'action, plus de « résolu » un-par-un, seuil
> healthcheck 1 h). Recette unit **2854/0**, cohérence **6/0**, front tsc0/vitest301 — **hook vert**.
> Déploiement **exit 0**, `/readyz` 200 stable, `NRestarts=0`. **Aucun retour arrière.**

---

## 1. Protéger les bonnes sauvegardes (fait d'abord, rien effacé)

- **Rotation suspendue de fait + bons dumps protégés** : hardlinks `GARDE-` (0 octet, **hors du glob
  de rotation** `labuse-labuse-*.dump`) posés sur les deux bons dumps du VPS, comme le fait déjà la
  rétention hebdo :
  - `GARDE-labuse-labuse-20261103-133003.dump` (6,2 Go, dump du jour)
  - `GARDE-labuse-labuse-20261102-163345.dump` (6,2 Go, veille)
  La prochaine sauvegarde n'est que **demain 13:30** ; aucune rotation imminente, et même si une
  tournait, elle ne peut plus toucher ces deux-là.
- **Au moins un dump complet récent SUR le VPS** : `labuse-labuse-20261103-133003.dump` **6,2 Go**,
  `pg_restore --list` = **1 760 entrées, 294 `TABLE DATA`** (tables clés présentes : parcels,
  parcel_flags, mvt_parcels, projets, comptes, data_sources, signal_instantanes, pige_biens), **0
  table exclue** (`.dump-tables-exclues.json` absent). Dump **sain**.
- **Au moins un dump complet récent HORS du VPS** : rapatrié sur le Mac
  (`~/labuse-backups/vps/labuse-labuse-20261103-133003.dump`, **6,1 Go**, `pg_restore --list` OK),
  + la veille (`20261102-163345`). Off-VPS désormais à jour **du jour même**.

> ⚠ Les hardlinks `GARDE-` sont une **protection temporaire** : à retirer (`rm GARDE-*`) une fois la
> garde anti-rétrécissement éprouvée sur un cycle, sinon ils épinglent l'inode d'un dump sorti de
> rotation (disque à 33 Go libres aujourd'hui — pas de pression).

## 2. Le « dump de 1,2 Mo » — enquête et correctif

**Constat : il n'y a aucun dump de 1,2 Mo.** Le fichier nommé dans le mandat
(`labuse-labuse-20261103-133003.dump`) pèse **6,2 Go** sur le VPS, et le job `backup-postgres` #9178
du 03/11 13:30→13:48 est **`ok`** (`taille_mo = 6559.8`). La prémisse « 1,2 Mo » ne correspond pas à
la réalité servie — **dit honnêtement**.

**Ce qui est vrai (la vraie faille) :** les sauvegardes du **01/11 et du 02/11 à 13:30 ont ÉCHOUÉ**
(`job_runs` #8280, #8726) — 01/11 : `LOCK TABLE … ACCESS SHARE` qui bute ; 02/11 : `pg_dump … FATAL:
terminating connection due to administrator command` (connexion coupée, collision avec le déploiement
de 13:12 ce jour-là). Ces échecs **ne laissent aucun fichier** (le script supprime un dump raté).
Puis le dump de 16:33 (02/11) et celui de 13:30 (03/11) ont réussi → les incidents se sont refermés
seuls. **Mais** le danger réel demeurait : les gardes du script (`non vide` + `pg_restore --list`)
**laissent passer un dump « petit mais valide »** (filet-par-table qui exclurait trop, base tronquée,
COPY coupé récolté partiel) — qui réussirait les contrôles puis **évincerait un bon dump en rotation**.
C'est exactement le scénario « 1,2 Mo » à prévenir.

**Correctif (`deploy/scripts/backup_postgres.sh`) — garde anti-rétrécissement :** avant toute rotation,
le dump neuf est comparé au **dernier bon dump existant** ; s'il fait **moins de 70 %** de sa taille
(`LABUSE_BACKUP_MIN_PCT`), la **rotation est ANNULÉE** (les bons dumps restent), le suspect est **mis
de côté sous `SUSPECT-…`** (hors du glob de rotation → ne peut pas se faire passer pour la dernière
bonne sauvegarde) et le script **échoue bruyamment (exit 1)** → incident + résumé du matin. Prouvé :
10 Mo passe, 0,1 Mo refusé, bon conservé (`tests/test_ops_nuit_1.py` + reproduction directe sous
bash). *(La vigie `ops_alertes` a déjà une alerte 30 % post-hoc ; la garde du script est la pièce
PRÉVENTIVE qui manquait.)* Commentaires « 4 conservés » corrigés en **2** (KEEP réel prod).

**Sauvegarde complète relancée + copiée hors VPS :** inutile de re-dumper (celui du jour est bon) ;
j'ai **rapatrié le dump du jour hors VPS** (cf. §1) — l'objectif « un bon dump récent sur et hors du
VPS » est atteint. La rotation reste active, désormais **gardée**.

## 3. Calcul de nuit en échec à 02:59 (Paris) = 05:59 (Réunion)

`job_runs` #9031 : `calcul-nuit` **02:00→05:59 Réunion (= 02:59 Paris)**, `echec`, durée **14 340 s**,
erreur **`InternalError: psycopg.errors.IdleInTransactionSessionTimeout`**. `q_v21` **absent** de
`parcel_p_score_v2` (runs présents : q_v20 servi, q_v18, q_v16, q_v11) → le calcul **n'a pas abouti**.

**Cause exacte.** Postgres a `idle_in_transaction_session_timeout = 120 s`. Le job `calcul_nuit`
ouvrait une transaction avec ses lectures de pré-vol puis **lançait le sous-process `flux-run` (~4 h)
en gardant cette connexion OUVERTE et INACTIVE** → Postgres l'a **tuée au bout de 2 min** ; au premier
usage d'après (mesures / commit final du runner), `IdleInTransactionSessionTimeout`. C'est le **seul**
moteur de l'échec enregistré. *(Second facteur de non-aboutissement : le budget valait 4 h depuis
02:00 → il courait jusqu'à ~06:00, PASSÉ la fenêtre 01 h–05 h.)*

**Correctif à la source (décision Vic, SANS toucher au timeout Postgres) :**
- `src/labuse/jobs_impl.py::calcul_nuit` — **aucune transaction tenue pendant le calcul Python** :
  pré-vol et mesures/promotion sont désormais en **sessions COURTES** (`session_scope()`), fermées
  avant/après le sous-process. Le job ne s'appuie plus sur `ctx.db` pendant les heures de calcul.
- **Budget borné par la fin de fenêtre** (`fin_h`), plus le timeout brut : ne mord jamais sur les
  heures ouvrées. Un dépassement = **abandon PROPRE et REPRENABLE** (`SousProcessTimeout` capturé) ;
  `flux-run --resume` saute les parcelles déjà faites → le run se **termine d'une nuit sur l'autre**.

**Durée réelle sur le VPS.** Mandat respecté : **je n'ai PAS relancé le calcul de jour sur la prod**.
Mesure par preuve : le sous-process a consommé **tout le budget (~4 h)** sans produire q_v21 → il faut
**plus que la fenêtre** (cohérent avec le « flux complet ~6 h » mesuré sur le Mac, cf. DEPLOY-FINAL).
Choix retenu : **découpe reprenable** (le mécanisme `--resume` existait déjà pour la cascade) plutôt
qu'élargir la fenêtre sur les heures du matin. Cette nuit, `calcul-nuit` **reprend à 02:00 sous gate
`LABUSE_CALCUL_NUIT_PROMEUT=0`** (inchangé) : il calcule/reprend, contrôle, et **le verdict part dans
le résumé du matin** — sans bascule.

## 4. Pourquoi le résumé du matin n'est pas arrivé

Il n'était **pas câblé** : aucun job « résumé du matin » n'existait (le `digest` est le mail CLIENT,
gelé ; la vigie `ops_alertes` n'émettait que des incidents). Ce que Vic attendait — le **verdict du
calcul de nuit** — n'est jamais parti non plus : `calcul-nuit` a **crashé (idle-tx, §3) avant son
étape de mail**. Seule la porte d'échec générique du runner a ouvert l'incident `job-echec:calcul-nuit`
(mailé, Brevo actif). **Correctif : un vrai job `resume-matin` (§6).**

## 5. État au 03/11

- **Passe Radar de la nuit** : `pige_passes` #378 (nouvelles) + #380 (relecture) le **02/11 23:16**,
  source **`auto`**, **119 nouvelles + 1 061 maj**, 0 hors-périmètre, 0 non-vérifiée. **Sain** (plus
  de verrou `running` figé : fix FIX-NU3-4 tenu).
- **Verrous** (sonde de nuit `coherence-robinets`, 03/11 07:27) : **32 joués, seul `G8` cassé**
  (connu, non bloquant — 7 sources vitrine « agent à 0 € », Radar à jour), **`V1c` à décider**
  (27 orphelines à purger au geste de Vic). **V3b/V4a/V6b verts.** Rien de nouveau cassé.
- **Banc de cohérence** : `coherence_runs` #18 (03/11 03:57), **`faux_client = 0`,
  `erreurs_lecteur = 0`**, 153 écarts connus (dual-source toléré) — le gate que lit `calcul-nuit`
  (faux_client + erreurs_lecteur) est **vert**.
- **Incidents ouverts** (12 au moment du déploiement, tous dans le résumé avec lien d'action) :
  calcul-nuit (échec de la nuit + jamais-réussi/escalade), `injection-b-en-attente` (2 sources
  structurantes classe B — **ton clic**), `verite-sources` (19 j) + escalade, `copie-externe-ancienne`
  (**15 j — branche le disque externe** ; l'off-VPS Mac, lui, est à jour), `restore-test-ancien`.

## 6. Mails (point 6, décision Vic) — refonte

- **(a) Plus de mail « résolu » un-par-un** : `resoudre()` referme l'incident en base sans mail ; les
  résolutions **remontent au résumé du matin** (section « rentré dans l'ordre depuis hier », 26 h).
- **(b) Résumé du matin quotidien** : nouveau job **`resume-matin`** (07:30 Réunion, après la sonde
  des verrous 07:25 et la passe Radar), **part TOUS les jours même « rien à signaler »** (son absence
  est elle-même un signal). Contenu : verdict calcul de nuit, sauvegardes (VPS + hors-VPS), Radar,
  verrous, cohérence, incidents ouverts (avec lien) et résolus depuis hier. *(Construit en lecture
  seule à la recette — rendu exact ci-dessus ; premier envoi réel demain 07:30.)*
- **(c) Sujets `[URGENT]` / `[INFO]`**, tout en français (`[URGENT]` = panne ou geste attendu).
- **(d) Lien d'action** (URL absolue `public_base_url`) dans chaque mail à geste et dans le résumé.
- **(e) Seuil de retard healthcheck à 1 h** : plancher `job_retard_seuil_min_h = 1.0` → un job
  fréquent (healthcheck 15 min) ne crie plus à 22 min.

## 7. Déploiement

- **Pré-vol** : 0 process lourd, 0 VACUUM, `/readyz` 200, `NRestarts=0`, disque 33 Go libres, dump du
  jour 6,2 Go présent. **Filets** (hardlinks) : `app-avant-ops-nuit1`, `venv-avant-ops-nuit1`,
  `Caddyfile.avant-ops-nuit1`, `labuse.env.avant-ops-nuit1`. Aucune migration, aucune nouvelle
  variable d'env, aucune nouvelle dépendance.
- **`deploy/scripts/deploy_app.sh labuse-vps`** = **exit 0** : deps importables (dont calcul-nuit),
  **crontab reposé == registre** (0 écart, `resume-matin` inclus → **34 jobs**), `deploiement.json =
  38c74a643431`, manifeste prod **q_v20** intact, `/readyz` **200 STABLE 25/25**.
- **Fumée** : `/healthz/crons` = **34**, `resume-matin` présent ; incident `/readyz` transitoire du
  restart **refermé** (healthcheck rejoué) ; **0 ERROR/5xx/lock_timeout** sur 10 min ; `/readyz` 200,
  `NRestarts=0` ; résumé du matin construit (lecture seule) **sans envoi non sollicité**.

### État final prod
Served **q_v20** · SHA **`38c74a643`** · `/readyz` 200 · `NRestarts=0`. Dumps : VPS
`20261103-133003` + `20261102-163345` (+ 2 `GARDE-`), Mac `20261103-133003` + `20261102-163345`.
`calcul-nuit` reprend cette nuit 02:00 (gate=0), `resume-matin` part demain 07:30.

### Retour arrière (prêt, non utilisé)
```bash
sudo systemctl stop labuse
sudo rm -rf /opt/labuse/app  && sudo mv /opt/labuse/app-avant-ops-nuit1  /opt/labuse/app
sudo rm -rf /opt/labuse/venv && sudo mv /opt/labuse/venv-avant-ops-nuit1 /opt/labuse/venv
sudo cp -p /etc/labuse/labuse.env.avant-ops-nuit1 /etc/labuse/labuse.env
sudo systemctl daemon-reload && sudo systemctl restart labuse && curl -fsS http://127.0.0.1:8000/readyz
# Schéma inchangé (aucune migration) → rien à défaire.
```

## Findings / dette (non bloquants)

1. **Nouveau job `resume-matin`** : tant qu'il n'a pas tourné une 1ʳᵉ fois (demain 07:30), la vigie le
   compte « jamais réussi » (même traitement que calcul-nuit/injection-nuit à leur arrivée) — se
   referme seul au 1ᵉʳ passage. Le résumé du matin de ce soir/demain le mentionnera.
2. **`flux-run` > fenêtre de nuit** : le run complet dépasse 4 h. Traité par la reprise d'une nuit sur
   l'autre ; si l'on veut un run complet en UNE nuit, élargir la fenêtre (`calcul_nuit_fin_h`) — la
   charge nocturne le permet, mais à arbitrer (collision avec les jobs de 06:40–07:00).
3. **Hardlinks `GARDE-`** : protection manuelle à retirer après un cycle de rotation gardée (sinon ils
   épinglent un inode sorti de rotation).
4. **`copie-externe` (disque externe) 15 j** : l'off-VPS Mac est à jour (pull du jour), mais le disque
   externe de Vic n'a pas été branché depuis 15 j — geste humain (dans le résumé, avec lien).
5. **Merge vers `main`** : `fix/ops-nuit-1` est poussée et déployée (le déploiement rsync la copie de
   travail). Le merge `fix/ops-nuit-1 → main` reste à faire **par PR** (pushes directs sur `main`
   gardés par le harnais). `deploiement.json` pointe le SHA de la branche (`38c74a643`).
