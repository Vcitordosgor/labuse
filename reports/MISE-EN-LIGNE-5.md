# MISE-EN-LIGNE-5 — préparer le serveur pour le classement (dim 22/11)

**Exécuté** dimanche 22/11, 09 h 27 → 10 h 50 Réunion (fenêtre ouverte, hors 13 h 30-14 h).
Un lot après l'autre. **ARRÊT au LOT 3** sur une preuve rouge (détail § LOT 3) — **le LOT 4
(mot de passe) n'a PAS été entamé**.

## LOT 1 — sauvegarde fraîche : VERT

`labuse jobs run backup-postgres` (le job habituel) — **ok en 18 min**. Dump
`labuse-labuse-20261122-092713.dump`, **6,2 Go**, **relu** (`pg_restore --list` : 1 849 lignes
TOC, **308 tables**). Place restante : **25 Go (74 %)** — suffisante.

## LOT 2 — purge des runs morts : DÉJÀ FAITE (no-op prouvé)

Revérifié aujourd'hui contre l'état réel : **aucun label de la liste figée MENAGE-PROD-1 §A
n'existe plus** (q_v11_m137, q_v13_sources1, q_v16, q_v21, q_v22, q_v24, seq 1/2/13 : 0 ligne
partout). La purge a eu lieu lors de MENAGE-PROD-1 (commit `6559b1fd4`). Ce qui subsiste : les
gardés (q_v20 servi, q_v19_sources, q_v18/seq 15, seq 17, q_v18_sources) **et q_v23** (hors
liste §A — intouché). **Rien à supprimer** : je n'ai pas exécuté de transaction vide. Manifeste
et gardés intacts.

## LOT 3 — PLU, geste minimal : APPLIQUÉ, mais preuve finale ROUGE (hors périmètre)

**Correction en cours de route (décision Vic, intégrée au script)** : le volet **peb a été
retiré**. L'écart « peb Mac 12 / prod 8 » n'était pas 4 manquants en prod mais **4 doublons côté
Mac** — les 4 zones Roland Garros A/B/C/D existent déjà en prod (une chacune) ; le Mac les a en
double. La prod fait foi ; pousser aurait dédoublé. (Cela corrige mon analyse erronée de
MISE-EN-LIGNE-2.)

**Appliqué en une transaction** (sauvegarde des lignes touchées d'abord, contrôles d'entrée ET
de sortie, empreintes géométriques zones+prescriptions vérifiées identiques Mac=prod le jour
même) :
- étiquette idurba : 97408 zones 246 + prescriptions 86 → `97408_PLU_20260625` ; 97411
  prescriptions 2 908 → `97411_PLU_20260805` (UPDATE 332 + 2 908, géométries intouchées) ;
- règlements des 2 communes = miroir Mac (397 → 553 ; l'ancien texte 97408 conservé = archive) ;
- table `plu_layer_archive` créée + 332 lignes ;
- ICPE **intouchées** (contrôle 1 271 dans la transaction) ; peb **intouchés** (contrôle 8).

**Preuves** :
1. ✅ la prod sert **`97408_PLU_20260625`** (zonage) et **`97411_PLU_20260805`** (règlement 241 +
   zones 259 + prescriptions 2 908) ;
3. ✅ empreinte parcelle→zone **inchangée** (97408 `e0ebb7f9…`, 97411 `b347cf4e…` = avant) ;
2. ⚠️ **`plu-veille-nuit` (lancé à la main, ok 56 s) : 21 communes à jour, mais 2 désynchronisées
   — Bras-Panon et Saint-Joseph.** Saint-Denis et La Possession sont bien **résolus**
   (`incidents_resolus: 2`). Les 2 restants **ne viennent pas de mon geste** : leur zonage servi
   en prod **= le Mac** (Bras-Panon `20260428`, Saint-Joseph `20251210`) — ce sont **2 nouveaux
   retards détectés par la sonde** (le GPU a publié plus récent que ce que le Mac *et* la prod
   servent). Les corriger suppose une ré-ingestion GPU sur le Mac — **hors de ce mandat**.

La preuve 2 étant formulée « aucun écart sur les 24 communes », elle est **rouge** → **ARRÊT**
(le LOT 4 touche l'authentification de toute la prod ; je ne l'entame pas sur un LOT 3 dont une
preuve n'est pas verte). Mon geste PLU est, lui, un **succès** (Saint-Denis + La Possession à
jour, zéro parcelle déplacée).

**Retour arrière du LOT 3** si besoin : lignes d'avant dans
`/var/backups/labuse/ml5-plu-20261122/` (reglement_avant, etiquettes_avant, peb_avant).

## LOT 4 — mot de passe : NON ENTAMÉ (arrêt au LOT 3)

## État final (10 h 50)

readyz 200 · run q_v20 / seq 17 intacts · disque 25 Go · temporaires purgés (sauvegarde LOT 3
conservée). **Décision pour Vic** : les 2 desync Bras-Panon/Saint-Joseph sont des retards GPU
préexistants hors périmètre — si tu les juges sans objet pour ce mandat, dis-le et j'enchaîne
sur le LOT 4 (mot de passe) ; sinon ils feront un geste PLU à part (ré-ingestion GPU côté Mac
puis même script).

---

# Suite (22/11, après validation du LOT 3 par Vic)

## LOT 4 — mot de passe de la base : FAIT, 4 preuves vertes

**Inventaire des usages (lecture seule d'abord).** Le secret = mot de passe du **rôle PG
`labuse`** (auth `scram-sha-256`, connexions TCP 127.0.0.1 seulement ; `postgres`/`labuse` en
`local` passent par `peer`, sans mot de passe). Il est à **2 endroits actifs sur le serveur** :
1. `LABUSE_DATABASE_URL` dans `/etc/labuse/labuse.env` → lu par l'API (systemd `EnvironmentFile`)
   et par **tous les crons** (ils sourcent `labuse.env`) ;
2. `/home/labuse/.pgpass` → lu par **`backup_postgres.sh`** (pg_dump/psql en `-h localhost -U labuse`).
**Côté Mac : AUCUN usage** — `labuse parite`, `aligner_base_prod.sh`, `sync-run.sh`,
`deploy_donnees.sh` lisent la prod via `ssh labuse-vps` + `sudo -u postgres psql` (peer).
À part : 17 copies `labuse.env.avant-*` (ancien secret) et `~/labuse-backups/M7_SECRETS.txt`
(Mac, non touché).

**Geste** : rotation atomique (script root sur le serveur, avec rollback intégré) — `ALTER ROLE
labuse` (secret alphanumérique 48 car. généré sur place par `openssl rand`, jamais affiché),
réécriture de `LABUSE_DATABASE_URL` et de `.pgpass`, `systemctl restart labuse`, et si `readyz`
n'était pas 200 → remise automatique de l'ancien mot de passe. *(Un premier essai a échoué
proprement sur un `SIGPIPE` à la génération — AVANT tout changement, prod intacte vérifiée ;
corrigé et rejoué.)*

**4 preuves** : ✅ readyz 200 après restart · ✅ un job du crontab se connecte (`healthcheck`
ok, 11:07) · ✅ la sauvegarde se connecte (chemin `.pgpass` + nouveau mot de passe →
`backup-auth-ok`) · ✅ `labuse parite` depuis le Mac fonctionne (FOND tout égal).

**Pour Vic** : le nouveau mot de passe est dans **`/root/labuse-db-password-20261122-110614.txt`
(0600 root)** sur le serveur. À faire par toi : le reporter dans ton coffre personnel
(`M7_SECRETS.txt` ou gestionnaire) — je n'y ai pas touché. **Rien d'autre à mettre à jour**
(serveur : env + .pgpass déjà faits ; Mac : n'utilise pas le secret). Les **17 copies
`labuse.env.avant-*` ne doivent JAMAIS servir de retour arrière** (ancien secret — y revenir
casserait l'auth et ré-exposerait le secret) ; à purger au ménage 48 h. Sauvegarde des 2
fichiers d'avant : `/root/ml5-mdp-avant-20261122-110614/`.

## Lecture seule — Bras-Panon et Saint-Joseph (méthode PLU-MAJ-2)

**La sonde a raison — ce n'est PAS un faux positif.** Comparaison par couche de l'idurba :

| | Bras-Panon (97402) | Saint-Joseph (97412) |
|---|---|---|
| Zonage servi (Mac=prod) | `97402_PLU_20260428` = **GPU en vigueur** | `97412_PLU_20251210` = **GPU en vigueur** |
| Règlement texte servi | `97402_PLU_20260428` ✅ | `97412_PLU_20251210` ✅ |
| **Prescriptions servies** (ER/EBC/mixité) | **`97402_PLU_20211020`** ❌ ancien | **`97412_PLU_20240320`** ❌ ancien |
| Doc GPU en vigueur (date appro · publié) | 28/04/2026 · publié GPU 30/06/2026 · Déclaration de Projet n°1 (mise en compatibilité) | 10/12/2025 · publié GPU 02/07/2026 · Modification n°5 (ouverture zone 2AU, OAP, règlt graphique) |

**1. Ce que la veille voit que l'ancien contrôle ne voyait pas.** Le zonage et le règlement ont
bien été ingérés au nouvel idurba, **mais la couche prescriptions est restée sur l'ancien
document**. L'ancien contrôle (compte de *features*) ne comparait pas l'idurba par couche ; la
sonde PLU-VEILLE-FIX-1, si. Ce n'est **pas une nouveauté depuis le 15/11** (docs GPU datés 30/06
et 02/07, **< 15/11**) : c'est un **angle mort antérieur** — FRAICHEUR-PROD-2 les disait « à
jour » faute de regarder la couche prescriptions.

**2. Ce qui change vraiment.** **Zone : 0 parcelle change de zone** (zonage déjà à jour, idurba
identique — confirmé via `zone-urba`). **Règlement : identique** (même idurba servi = GPU) →
**aucune règle calibrée touchée**. Le seul écart réel est la couche **prescriptions**. Les deux
procédures (DP n°1, Modif n°5) sont de **vraies modifications** → les prescriptions (ER/EBC/
servitudes) ont vraisemblablement changé ; **l'ampleur exacte (parcelles portant une prescription
modifiée) n'est pas chiffrable sans télécharger le jeu GPU** — le Mac ne l'a pas (il porte lui
aussi l'ancien idurba de prescriptions).

**3. Conclusion : vraie mise à jour, pas un ré-étiquetage.** Contrairement à La Possession (où
le Mac avait déjà le bon idurba, simple étiquette à re-pointer), ici **ni le Mac ni la prod n'ont
le nouvel idurba des prescriptions** → il faut **ré-ingérer les prescriptions des 2 communes
depuis le GPU** (sur le Mac d'abord), puis un geste de fond. Mais comme **zonage et règlement
sont déjà à jour**, l'impact se limite aux parcelles portant une prescription (ER/EBC) dans ces
2 communes — pas au zonage. Ces prescriptions étaient déjà en retard avant q_v23, donc **ce n'est
pas une régression de ce mandat** ; c'est un geste PLU amont à planifier (hors de cette fenêtre).

## Point 4 — budget disque de la chaîne q_v25, chiffres du 22/11

**Mon plan d'hier annonçait 14,7 Go à libérer par la purge : c'était faux** — cette purge était
déjà faite (MENAGE-PROD-1). Budget réel du jour :
- **Place libre : 25 Go (74 %)**, stable. Dumps en rotation : 1 hebdo + 2 quotidiens ≈ 18 Go ;
  la sauvegarde de 13 h 30 remplace un quotidien → **pas de croissance nette**.
- **Besoin de la chaîne q_v25** ≈ poids d'un run complet, mesuré sur q_v23 : cascade 3,05 Go +
  score 1,57 + p_score 0,45 + évaluations 0,04 + résiduel 0,07 = **~5,2 Go**, + overhead de
  calcul (WAL/temp) ~1-2 Go → **~6-7 Go**.
- **Marge** : 25 − 7 ≈ **18 Go libres au plus serré**, **très au-dessus du plancher de 3 Go**.
- **q_v23 pèse ~5,2 Go** (il reste présent : cascade seq 18 + score + p_score). **Pas besoin de
  le purger** pour le budget. Optionnel : le purger donnerait +5 Go de marge, mais il est utile
  en comparaison (dernier candidat) et hors de la liste figée §A — je ne le touche pas.

**Conclusion** : la chaîne q_v25 tient largement sans aucune purge supplémentaire.
